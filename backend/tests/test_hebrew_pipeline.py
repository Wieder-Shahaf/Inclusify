"""
Tests for the Hebrew analysis pipeline fixes.

Covers the regression where every Hebrew finding was discarded:
- _LGBTQ_SIGNALS contained only English stems, so Hebrew phrases were
  dropped as "hallucinations" and Hebrew documents always scored 100.
- The model occasionally answers with Hebrew severity labels, near-miss
  phrases (dropped characters), and code-switched (CJK) explanations or
  suggestions.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

HEBREW_SENTENCE = (
    "מחקרים על הומוסקסואלים הראו כי הפרעת זהות מגדרית הייתה נפוצה בקרב הנבדקים."
)


def _mock_client(issue: dict) -> MagicMock:
    client = MagicMock()
    client.analyze_sentence = AsyncMock(return_value={"issues": [issue]})
    client.get_suggestion = AsyncMock(return_value=None)
    return client


class TestHebrewSeverityMapping:
    def test_hebrew_severity_labels_map(self):
        from app.modules.analysis.llm_client import map_severity

        assert map_severity("מיושן") == "outdated"
        assert map_severity("מוטה") == "biased"
        assert map_severity("פוגעני פוטנציאלי") == "potentially_offensive"
        assert map_severity("עלול לפגוע") == "potentially_offensive"
        assert map_severity("שגוי עובדתית") == "factually_incorrect"

    def test_english_labels_still_map(self):
        from app.modules.analysis.llm_client import map_severity

        assert map_severity("Outdated") == "outdated"
        assert map_severity("Correct") is None


class TestPhraseRepair:
    def test_repairs_dropped_leading_character(self):
        from app.modules.analysis.hybrid_detector import _repair_phrase

        chunk = HEBREW_SENTENCE
        # Model dropped the leading ה
        repaired = _repair_phrase(chunk, "פרעת זהות מגדרית")
        assert repaired is not None
        assert repaired in chunk

    def test_rejects_unrelated_phrase(self):
        from app.modules.analysis.hybrid_detector import _repair_phrase

        assert _repair_phrase(HEBREW_SENTENCE, "completely unrelated text") is None


class TestHebrewDetection:
    @pytest.mark.asyncio
    async def test_hebrew_finding_survives_signal_filter(self):
        """A Hebrew phrase must not be dropped as an off-topic hallucination."""
        from app.modules.analysis.hybrid_detector import HybridDetector

        client = _mock_client({
            "phrase": "הומוסקסואלים",
            "category": "Demeaning Terminology",
            "severity": "Outdated",
            "explanation": "שם עצם קליני מיושן.",
            "suggestion": "גברים הומואים ונשים לסביות",
            "confidence": 0.7,
        })
        detector = HybridDetector(vllm_client=client)
        issues, _, _ = await detector.analyze(HEBREW_SENTENCE, language="he")

        assert len(issues) == 1
        assert issues[0].phrase == "הומוסקסואלים"
        assert issues[0].severity == "outdated"

    @pytest.mark.asyncio
    async def test_cjk_suggestion_and_explanation_are_dropped(self):
        """Code-switched CJK output must never reach the user."""
        from app.modules.analysis.hybrid_detector import HybridDetector

        client = _mock_client({
            "phrase": "הומוסקסואלים",
            "category": "Demeaning Terminology",
            "severity": "Outdated",
            "explanation": "מונח מיושן 生活习惯 בהקשר אקדמי.",
            "suggestion": "生活习惯的同性恋",
            "confidence": 0.7,
        })
        detector = HybridDetector(vllm_client=client)
        issues, _, _ = await detector.analyze(HEBREW_SENTENCE, language="he")

        assert len(issues) == 1
        assert issues[0].description == ""
        assert issues[0].suggestion is None

    @pytest.mark.asyncio
    async def test_near_miss_phrase_gets_exact_offsets(self):
        """A phrase with a dropped character is repaired and located in the text."""
        from app.modules.analysis.hybrid_detector import HybridDetector

        client = _mock_client({
            "phrase": "פרעת זהות מגדרית",  # missing leading ה
            "category": "Medicalization",
            "severity": "Outdated",
            "explanation": "מונח שהוסר מה-DSM-5.",
            "suggestion": "דיספוריה מגדרית",
            "confidence": 0.8,
        })
        detector = HybridDetector(vllm_client=client)
        issues, _, _ = await detector.analyze(HEBREW_SENTENCE, language="he")

        assert len(issues) == 1
        issue = issues[0]
        assert issue.phrase in HEBREW_SENTENCE
        assert HEBREW_SENTENCE[issue.start:issue.end] == issue.phrase

    @pytest.mark.asyncio
    async def test_english_finding_unaffected(self):
        """English path behaves exactly as before."""
        from app.modules.analysis.hybrid_detector import HybridDetector

        sentence = "Research on homosexuals showed that the lifestyle is harmful."
        client = _mock_client({
            "phrase": "homosexuals",
            "category": "Demeaning Terminology",
            "severity": "Outdated",
            "explanation": "Dehumanizing clinical noun.",
            "suggestion": "gay and lesbian people",
            "confidence": 0.9,
        })
        detector = HybridDetector(vllm_client=client)
        issues, _, _ = await detector.analyze(sentence, language="en")

        assert len(issues) == 1
        assert issues[0].phrase == "homosexuals"
        assert issues[0].suggestion == "gay and lesbian people"
