"""
Hybrid detector for LGBTQ+ inclusive language analysis.

Combines LLM-based contextual analysis with rule-based term detection.
LLM results are preferred for overlapping spans; rule-based serves as fallback.
"""

import asyncio
import logging
from typing import TYPE_CHECKING

from app.modules.analysis.call_metrics import CallMetrics
from app.modules.analysis.llm_client import VLLMClient, map_severity
from app.modules.analysis.sentence_splitter import split_with_offsets

if TYPE_CHECKING:
    from app.modules.analysis.router import Issue

logger = logging.getLogger(__name__)


def calculate_overlap(issue1: "Issue", issue2: "Issue") -> float:
    """
    Calculate the overlap ratio between two issues based on character positions.

    Args:
        issue1: First issue with start/end positions
        issue2: Second issue with start/end positions

    Returns:
        Overlap ratio from 0.0 (no overlap) to 1.0 (full overlap).
        Ratio is calculated as overlap_chars / min(len1, len2).
    """
    # Calculate overlap range
    overlap_start = max(issue1.start, issue2.start)
    overlap_end = min(issue1.end, issue2.end)
    overlap_chars = max(0, overlap_end - overlap_start)

    # Calculate lengths
    len1 = issue1.end - issue1.start
    len2 = issue2.end - issue2.start

    if min(len1, len2) == 0:
        return 0.0

    return overlap_chars / min(len1, len2)


def merge_results(
    llm_issues: list["Issue"],
    rule_issues: list["Issue"],
    overlap_threshold: float = 0.5
) -> list["Issue"]:
    """
    Merge LLM and rule-based detection results, preferring LLM for overlapping spans.

    Args:
        llm_issues: Issues detected by LLM analysis
        rule_issues: Issues detected by rule-based matching
        overlap_threshold: Minimum overlap ratio to consider duplicates (default 0.5)

    Returns:
        Merged list of issues, sorted by start position.
        LLM issues are always included; rule issues only if not overlapping with LLM.
    """
    # Start with all LLM issues
    merged = list(llm_issues)

    # Add rule issues only if they don't overlap significantly with LLM issues
    for rule_issue in rule_issues:
        overlaps_with_llm = False
        for llm_issue in llm_issues:
            if calculate_overlap(rule_issue, llm_issue) >= overlap_threshold:
                overlaps_with_llm = True
                break

        if not overlaps_with_llm:
            merged.append(rule_issue)

    # Sort by start position
    merged.sort(key=lambda x: x.start)

    return merged


def detect_language(text: str) -> str:
    """
    Detect language of text using simple heuristics.

    Args:
        text: Input text

    Returns:
        'he' if Hebrew characters detected, 'en' otherwise
    """
    # Check for Hebrew characters (Unicode range)
    hebrew_chars = sum(1 for c in text if '\u0590' <= c <= '\u05FF')
    if hebrew_chars > 0:
        return 'he'
    return 'en'


class HybridDetector:
    """
    Hybrid detector combining LLM and rule-based analysis.

    Uses LLM for contextual analysis of each sentence, falls back to rules on failure.
    Tracks which method was used and reports mode in response.
    """

    def __init__(self, vllm_client: VLLMClient = None):
        """
        Initialize hybrid detector.

        Args:
            vllm_client: Optional VLLMClient instance (creates default if not provided)
        """
        self.client = vllm_client or VLLMClient()

    async def analyze(
        self,
        text: str,
        language: str = "auto"
    ) -> tuple[list["Issue"], str, CallMetrics]:
        """
        Analyze text for LGBTQ+ inclusive language issues.

        Args:
            text: Text to analyze
            language: Language code ('en', 'he', 'auto'). Auto-detects if 'auto'.

        Returns:
            Tuple of (issues_list, analysis_mode, call_metrics).
            analysis_mode is 'llm', 'hybrid', or 'rules_only'.
            call_metrics holds aggregated vLLM call stats for this request.
        """
        # Import here to avoid circular import
        from app.modules.analysis.router import Issue, detect_rule_based_issues

        # Detect language if auto
        if language == "auto":
            language = detect_language(text)

        # Split text into sentences with offsets
        sentences = split_with_offsets(text, language)
        logger.info(
            "Hybrid detection started: text_length=%d language=%s sentences=%d",
            len(text), language, len(sentences),
        )

        llm_issues: list[Issue] = []
        llm_success_count = 0
        llm_failure_count = 0
        call_metrics = CallMetrics(total_sentences=len(sentences))

        # Process sentences in PARALLEL with asyncio.gather
        async def analyze_one(sentence: str, start_offset: int, end_offset: int):
            result = await self.client.analyze_sentence(sentence, metrics=call_metrics)
            return (result, sentence, start_offset, end_offset)

        # Run all analyses concurrently
        tasks = [analyze_one(s, start, end) for s, start, end in sentences]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for item in results:
            if isinstance(item, Exception):
                llm_failure_count += 1
                continue

            result, sentence, start_offset, end_offset = item

            if result is not None:
                llm_success_count += 1

                # Map severity and create issue if not "Correct"
                severity = map_severity(result.get("severity", ""))
                if severity is not None:
                    # Safely extract string fields (handle nan/None)
                    category = result.get("category", "LLM Detected")
                    if not isinstance(category, str) or category != category:  # nan check
                        category = "LLM Detected"
                    explanation = result.get("explanation", "")
                    if not isinstance(explanation, str) or explanation != explanation:
                        explanation = ""

                    # Extract and clamp confidence to [0.0, 1.0]
                    confidence_raw = result.get("confidence")
                    if isinstance(confidence_raw, (int, float)) and confidence_raw == confidence_raw:
                        confidence = max(0.0, min(1.0, float(confidence_raw)))
                    else:
                        confidence = None

                    issue = Issue(
                        flagged_text=sentence,
                        severity=severity,
                        type=category,
                        description=explanation,
                        suggestion=None,
                        start=start_offset,
                        end=end_offset,
                        confidence=confidence,
                    )
                    llm_issues.append(issue)
            else:
                llm_failure_count += 1

        logger.info(
            "LLM analysis completed: sentences=%d llm_success=%d llm_failure=%d llm_issues=%d",
            len(sentences), llm_success_count, llm_failure_count, len(llm_issues),
        )

        # Run rule-based detection on full text
        rule_issues = detect_rule_based_issues(text)
        logger.info("Rule-based detection returned: rule_issues=%d", len(rule_issues))

        # Merge results (LLM preferred for overlapping spans)
        merged_issues = merge_results(llm_issues, rule_issues)
        logger.info(
            "Merge completed: llm_issues=%d rule_issues=%d merged_total=%d",
            len(llm_issues), len(rule_issues), len(merged_issues),
        )

        # Determine analysis mode
        total_sentences = len(sentences)
        if total_sentences == 0:
            mode = "rules_only"
        elif llm_failure_count == 0:
            mode = "llm"
        elif llm_success_count == 0:
            mode = "rules_only"
        else:
            mode = "hybrid"

        if mode == "rules_only" and total_sentences > 0:
            logger.warning("LLM unavailable for all sentences — falling back to rules_only mode")

        return merged_issues, mode, call_metrics


__all__ = ["HybridDetector", "calculate_overlap", "merge_results", "detect_language", "CallMetrics"]
