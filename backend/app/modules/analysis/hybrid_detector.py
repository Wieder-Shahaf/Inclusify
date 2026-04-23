"""
LLM detector for LGBTQ+ inclusive language analysis.

Uses LLM-based contextual analysis exclusively. When the LLM is unavailable
(circuit breaker open or all sentences fail), returns empty results with
analysis_mode='rules_only' so the frontend can surface the appropriate message.
"""

import asyncio
import logging
import re as _re
from typing import TYPE_CHECKING, Optional

from pybreaker import CircuitBreakerError

from app.modules.analysis.call_metrics import CallMetrics
from app.modules.analysis.circuit_breaker import vllm_breaker
from app.modules.analysis.llm_client import VLLMClient, map_severity
from app.modules.analysis.sentence_splitter import split_with_offsets

if TYPE_CHECKING:
    from app.modules.analysis.router import Issue

logger = logging.getLogger(__name__)

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
    """LLM + DB-rules detector for LGBTQ+ inclusive language analysis."""

    def __init__(self, vllm_client: VLLMClient = None):
        self.client = vllm_client or VLLMClient()

    async def _load_db_rules(self, pool) -> list[dict]:
        """Fetch enabled rules from DB. Returns empty list on any failure."""
        if pool is None:
            return []
        try:
            import re as _re_mod
            async with pool.acquire(timeout=3.0) as conn:
                rows = await conn.fetch(
                    "SELECT term, default_severity, category, pattern_type, pattern_value "
                    "FROM rules WHERE is_enabled = TRUE LIMIT 500"
                )
                rules = []
                for row in rows:
                    rules.append(dict(row))
                return rules
        except Exception:
            logger.warning("Could not load rules from DB — skipping rule-based pass")
            return []

    def _apply_rules(self, text: str, rules: list[dict]) -> list["Issue"]:
        """Apply DB rules to text, return Issues for matches not already covered by LLM."""
        import re as _re_mod
        from app.modules.analysis.router import Issue
        issues = []
        for rule in rules:
            pattern_type = rule.get("pattern_type", "exact")
            pattern_value = rule.get("pattern_value") or rule.get("term", "")
            if not pattern_value:
                continue
            try:
                if pattern_type == "regex":
                    matches = list(_re_mod.finditer(pattern_value, text, _re_mod.IGNORECASE))
                else:
                    matches = list(_re_mod.finditer(
                        _re_mod.escape(pattern_value), text, _re_mod.IGNORECASE
                    ))
            except _re_mod.error:
                continue
            for m in matches:
                issues.append(Issue(
                    flagged_text=m.group(0),
                    severity=rule.get("default_severity", "outdated"),
                    type=rule.get("category") or "Rule Match",
                    description=f"Flagged by rule: {rule.get('term', pattern_value)}",
                    suggestion=None,
                    phrase=m.group(0),
                    start=m.start(),
                    end=m.end(),
                    confidence=1.0,
                ))
        return issues

    async def analyze(
        self,
        text: str,
        language: str = "auto",
        chunks: Optional[list[str]] = None,
        db_pool=None,
    ) -> tuple[list["Issue"], str, CallMetrics]:
        """
        Analyze text for LGBTQ+ inclusive language issues using LLM + DB rules.

        Returns:
            Tuple of (issues_list, analysis_mode, call_metrics).
            analysis_mode is 'llm' when at least one sentence was processed,
            or 'rules_only' when LLM was completely unavailable.
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

        logger.info(
            "LLM detection started: text_length=%d language=%s sentences=%d",
            len(text), language, len(sentences),
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

            result, sentence, start_offset, end_offset = item

            if result is not None:
                llm_success_count += 1

                severity = map_severity(result.get("severity", ""))
                if severity is not None:
                    category = result.get("category", "LLM Detected")
                    if not isinstance(category, str) or category != category:
                        category = "LLM Detected"
                    explanation = result.get("explanation", "")
                    if not isinstance(explanation, str) or explanation != explanation:
                        explanation = ""

                    confidence_raw = result.get("confidence")
                    if isinstance(confidence_raw, (int, float)) and confidence_raw == confidence_raw:
                        confidence = max(0.0, min(1.0, float(confidence_raw)))
                    else:
                        confidence = None

                    suggestion = result.get("suggestion")
                    if not isinstance(suggestion, str) or not suggestion.strip() or suggestion.strip().lower() == "null":
                        if vllm_breaker.current_state != "open":
                            suggestion = await self.client.get_suggestion(
                                sentence, severity, category, metrics=call_metrics
                            )
                        else:
                            suggestion = None

                    inclusive_sentence = result.get("inclusive_sentence")
                    if not isinstance(inclusive_sentence, str) or not inclusive_sentence.strip() or inclusive_sentence.strip().lower() == "null":
                        inclusive_sentence = None

                    phrase = result.get("phrase")
                    if not isinstance(phrase, str) or not phrase.strip() or phrase.strip().lower() == "null":
                        phrase = None

                    # Narrow offsets to the phrase when the LLM returned one.
                    # Fall back to the full sentence span when phrase is absent or
                    # not locatable (e.g. LLM hallucinated a different form).
                    actual_start = start_offset
                    actual_end = end_offset
                    if phrase:
                        phrase_idx = sentence.find(phrase)
                        if phrase_idx == -1:
                            # Case-insensitive fallback
                            phrase_idx = sentence.lower().find(phrase.lower())
                        if phrase_idx != -1:
                            actual_start = start_offset + phrase_idx
                            actual_end = actual_start + len(phrase)

                    issue = Issue(
                        flagged_text=sentence,
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
            mode = "rules_only"
        else:
            mode = "llm"

        # Apply DB-managed rules as an additional pass; deduplicate by span overlap
        db_rules = await self._load_db_rules(db_pool)
        if db_rules:
            rule_issues = self._apply_rules(text, db_rules)
            llm_spans = {(i.start, i.end) for i in llm_issues}
            new_rule_issues = [
                ri for ri in rule_issues
                if not any(
                    ri.start < ls_end and ri.end > ls_start
                    for ls_start, ls_end in llm_spans
                )
            ]
            if new_rule_issues:
                logger.info("DB rules added %d issue(s) not found by LLM", len(new_rule_issues))
            llm_issues = llm_issues + new_rule_issues

        return llm_issues, mode, call_metrics


__all__ = ["HybridDetector", "detect_language", "CallMetrics"]
