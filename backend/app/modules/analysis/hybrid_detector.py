"""
LLM detector for LGBTQ+ inclusive language analysis.

Uses LLM-based contextual analysis exclusively. When the LLM is unavailable
(circuit breaker open or all sentences fail), returns empty results with
analysis_mode='llm'.
"""

import asyncio
import logging
import re as _re
from typing import TYPE_CHECKING, Optional

from app.modules.analysis.call_metrics import CallMetrics
from app.modules.analysis.circuit_breaker import vllm_breaker
from app.modules.analysis.llm_client import VLLMClient, map_severity, extract_chunk_issues
from app.modules.analysis.sentence_splitter import split_with_offsets

if TYPE_CHECKING:
    from app.modules.analysis.router import Issue

logger = logging.getLogger(__name__)

def _find_references_start(text: str) -> int:
    """
    Return the char offset where the references/bibliography section begins,
    or len(text) if no such section is found. Uses the LAST match so that
    inline mentions of the word 'references' don't trigger early cutoff.
    """
    pattern = _re.compile(
        r'(?:^|\n)[ \t]*'
        r'(?:REFERENCES|References|BIBLIOGRAPHY|Bibliography|'
        r'Works\s+Cited|WORKS\s+CITED|Literature\s+Cited|LITERATURE\s+CITED)'
        r'[ \t]*(?:\n|$)',
        _re.MULTILINE,
    )
    matches = list(pattern.finditer(text))
    if not matches:
        return len(text)
    return matches[-1].start()


# Terms that ARE the recommended inclusive vocabulary per APA/GLAAD —
# flagging them as problematic is always a false positive.
_SAFE_PHRASES: frozenset[str] = frozenset({
    "sexual orientation",
    "gender identity",
    "gender expression",
    "lgbtq+",
})


def _deduplicate_issues(issues: list) -> list:
    """
    Remove duplicate LLM issues within a single run:
    1. Identical phrase (case-insensitive) → keep highest-confidence entry.
    2. Span fully contained within an already-kept span → drop the inner one.
    """
    if not issues:
        return issues

    # Step 1: per-phrase dedup — keep highest confidence
    by_phrase: dict[str, object] = {}
    no_phrase: list = []
    for iss in issues:
        if not iss.phrase:
            no_phrase.append(iss)
            continue
        key = iss.phrase.strip().lower()
        prev = by_phrase.get(key)
        if prev is None or (iss.confidence or 0.0) > (prev.confidence or 0.0):
            by_phrase[key] = iss

    candidates = list(by_phrase.values()) + no_phrase

    # Step 2: span containment dedup — sort by confidence desc, drop dominated spans
    result: list = []
    for iss in sorted(candidates, key=lambda i: (i.confidence or 0.0), reverse=True):
        if any(kept.start <= iss.start and iss.end <= kept.end for kept in result):
            continue
        result.append(iss)

    return result


def _locate_chunks(full_text: str, chunks: list[str]) -> list[tuple[str, int, int]]:
    """
    Find character offsets of HybridChunker chunks within the analysis text.
    Falls back progressively: exact → skip heading line → whitespace-normalized.
    Chunks that still fail (e.g. table cells, bibliography) are silently skipped.
    """
    result = []
    skipped = 0
    search_start = 0

    _ws_norm = _re.compile(r'\s+')
    full_text_normalized = _ws_norm.sub(' ', full_text)

    for raw in chunks:
        stripped = raw.strip()
        if not stripped:
            continue

        # 1. Exact match
        idx = full_text.find(stripped, search_start)

        # 2. Skip first line (heading context prepended by chunker)
        if idx == -1:
            lines = [ln for ln in stripped.split('\n') if ln.strip()]
            if len(lines) > 1:
                content = '\n'.join(lines[1:]).strip()
                idx = full_text.find(content, search_start)
                if idx != -1:
                    stripped = content

        # 3. Whitespace-normalized match (recovers double-space / tab differences)
        if idx == -1:
            norm_chunk = _ws_norm.sub(' ', stripped)
            norm_idx = full_text_normalized.find(norm_chunk, search_start)
            if norm_idx != -1:
                orig_idx = full_text.find(norm_chunk[0], search_start)
                if orig_idx != -1:
                    idx = orig_idx
                    stripped = full_text[orig_idx: orig_idx + len(norm_chunk)]

        if idx != -1:
            result.append((stripped, idx, idx + len(stripped)))
            search_start = idx + len(stripped)
        else:
            skipped += 1
            logger.debug("HybridChunker chunk not located, skipping: %.60r", stripped)

    if skipped:
        logger.info(
            "HybridChunker: %d/%d chunks located; %d skipped (likely tables/bibliography)",
            len(result), len(result) + skipped, skipped,
        )
    return result


def detect_language(text: str) -> str:
    """Detect language: 'he' if Hebrew characters present, 'en' otherwise."""
    hebrew_chars = sum(1 for c in text if '\u0590' <= c <= '\u05FF')
    if hebrew_chars > 0:
        return 'he'
    return 'en'


class HybridDetector:
    """LLM detector for LGBTQ+ inclusive language analysis."""

    def __init__(self, vllm_client: VLLMClient = None):
        self.client = vllm_client or VLLMClient()

    async def analyze(
        self,
        text: str,
        language: str = "auto",
        chunks: Optional[list[str]] = None,
    ) -> tuple[list["Issue"], str, CallMetrics]:
        """
        Analyze text for LGBTQ+ inclusive language issues using LLM + DB rules.

        Returns:
            Tuple of (issues_list, analysis_mode, call_metrics).
            analysis_mode is 'llm' when at least one sentence was processed,
            'llm' in all cases.
        """
        from app.modules.analysis.router import Issue

        if language == "auto":
            language = detect_language(text)

        if chunks:
            sentences = _locate_chunks(text, chunks)
            if not sentences:
                logger.warning("HybridChunker offset location failed for all chunks, falling back to sentence splitter")
                sentences = split_with_offsets(text, language)
        else:
            sentences = split_with_offsets(text, language)

        # Skip chunks that fall entirely within the references/bibliography section —
        # citation titles and author names generate high-volume false positives.
        refs_start = _find_references_start(text)
        if refs_start < len(text):
            before = len(sentences)
            sentences = [(s, st, en) for s, st, en in sentences if st < refs_start]
            logger.info(
                "References section detected at offset %d — dropped %d chunk(s)",
                refs_start, before - len(sentences),
            )

        logger.info(
            "LLM detection started: text_length=%d language=%s sentences=%d refs_start=%d",
            len(text), language, len(sentences), refs_start,
        )

        llm_issues: list[Issue] = []
        llm_success_count = 0
        llm_failure_count = 0
        call_metrics = CallMetrics(total_sentences=len(sentences))

        async def analyze_one(sentence: str, start_offset: int, end_offset: int):
            # Skip immediately if circuit is already open — no point queuing.
            if vllm_breaker.current_state == "open":
                return None, sentence, start_offset, end_offset
            result = await self.client.analyze_sentence(sentence, metrics=call_metrics)
            return (result, sentence, start_offset, end_offset)

        tasks = [analyze_one(s, start, end) for s, start, end in sentences]
        # Overall safety cap: 3 min for the entire analysis regardless of document size.
        try:
            results = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=180)
        except asyncio.TimeoutError:
            logger.warning("Analysis hit overall 180s timeout — returning partial results")
            results = []

        for item in results:
            if isinstance(item, Exception):
                llm_failure_count += 1
                continue

            result, chunk, start_offset, end_offset = item

            if result is not None:
                llm_success_count += 1

                for issue_data in extract_chunk_issues(result):
                    severity = map_severity(issue_data.get("severity", ""))
                    if severity is None:
                        continue

                    # Drop hallucinated issues where the phrase has no LGBTQ+ signal.
                    phrase_lower = (issue_data.get("phrase") or "").lower().strip()
                    _LGBTQ_SIGNALS = {
                        "gay", "lesbian", "bisexual", "transgender", "trans", "queer",
                        "nonbinary", "non-binary", "lgbtq", "lgbt", "homosexual",
                        "heterosexual", "cisgender", "cis", "gender", "sexual",
                        "orientation", "identity", "dysphoria", "same-sex", "lifestyle",
                        "passing", "transitioning", "pronoun", "assigned", "deviant",
                        "pervert", "trann", "sodomit", "conversion", "reparative",
                    }
                    if phrase_lower and not any(sig in phrase_lower for sig in _LGBTQ_SIGNALS):
                        logger.debug("Dropping off-topic LLM issue: phrase=%r", phrase_lower)
                        continue

                    # Drop false positives on APA/GLAAD-recommended inclusive terms.
                    if phrase_lower in _SAFE_PHRASES:
                        logger.debug("Dropping safe-phrase false positive: %r", phrase_lower)
                        continue

                    category = issue_data.get("category", "LLM Detected")
                    if not isinstance(category, str):
                        category = "LLM Detected"
                    explanation = issue_data.get("explanation", "")
                    if not isinstance(explanation, str):
                        explanation = ""

                    suggestion = issue_data.get("suggestion")
                    if not isinstance(suggestion, str) or not suggestion.strip() or suggestion.strip().lower() == "null":
                        if vllm_breaker.current_state != "open":
                            suggestion = await self.client.get_suggestion(
                                chunk, severity, category, metrics=call_metrics
                            )
                        else:
                            suggestion = None
                    # Drop suggestions that are identical to the flagged phrase —
                    # these are truncated/degenerate model outputs with no value.
                    phrase_for_cmp = issue_data.get("phrase") or ""
                    if suggestion and phrase_for_cmp and suggestion.strip() == phrase_for_cmp.strip():
                        suggestion = None

                    inclusive_sentence = issue_data.get("inclusive_sentence")
                    if not isinstance(inclusive_sentence, str) or not inclusive_sentence.strip() or inclusive_sentence.strip().lower() == "null":
                        inclusive_sentence = None

                    phrase = issue_data.get("phrase")
                    if not isinstance(phrase, str) or not phrase.strip() or phrase.strip().lower() == "null":
                        phrase = None

                    # Narrow offsets to the phrase span within the chunk.
                    # Fall back to full chunk span when phrase is absent or not locatable.
                    actual_start = start_offset
                    actual_end = end_offset
                    if phrase:
                        phrase_idx = chunk.find(phrase)
                        if phrase_idx == -1:
                            phrase_idx = chunk.lower().find(phrase.lower())
                        if phrase_idx != -1:
                            actual_start = start_offset + phrase_idx
                            actual_end = actual_start + len(phrase)

                    confidence_raw = issue_data.get("confidence")
                    confidence = (
                        max(0.0, min(1.0, float(confidence_raw)))
                        if isinstance(confidence_raw, (int, float)) and confidence_raw == confidence_raw
                        else None
                    )

                    issue = Issue(
                        flagged_text=chunk,
                        severity=severity,
                        type=category,
                        description=explanation,
                        suggestion=suggestion,
                        inclusive_sentence=inclusive_sentence,
                        phrase=phrase,
                        start=actual_start,
                        end=actual_end,
                        confidence=confidence,
                    )
                    llm_issues.append(issue)
            else:
                llm_failure_count += 1

        logger.info(
            "LLM analysis completed: sentences=%d success=%d failure=%d issues=%d",
            len(sentences), llm_success_count, llm_failure_count, len(llm_issues),
        )

        if llm_success_count == 0:
            logger.warning("LLM unavailable for all sentences — returning empty results")
        mode = "llm"

        # Drop issues with no usable confidence score.
        before_conf = len(llm_issues)
        llm_issues = [i for i in llm_issues if i.confidence is not None and i.confidence > 0]
        if len(llm_issues) < before_conf:
            logger.info("Confidence filter removed %d issue(s) with null/zero confidence", before_conf - len(llm_issues))

        # Deduplicate LLM issues (same phrase, overlapping spans).
        before_dedup = len(llm_issues)
        llm_issues = _deduplicate_issues(llm_issues)
        if len(llm_issues) < before_dedup:
            logger.info("Dedup removed %d duplicate issue(s)", before_dedup - len(llm_issues))

        return llm_issues, mode, call_metrics


__all__ = ["HybridDetector", "detect_language", "CallMetrics"]
