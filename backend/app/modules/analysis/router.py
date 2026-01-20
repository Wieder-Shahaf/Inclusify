"""
Analysis Router - LGBTQ+ Inclusive Language Detection

=============================================================================
                            DEMO / PLACEHOLDER
=============================================================================
This module currently uses RULE-BASED detection as a placeholder.

In production, this will be replaced with:
- Fine-tuned LLM (lightblue/suzume-llama-3-8B-multilingual)
- QLoRA adapter weights trained on LGBTQ+ inclusive language corpus
- Azure ML Online Endpoint for inference

The rule-based approach below serves as:
1. A working demo for stakeholder presentations
2. A fallback when the model endpoint is unavailable
3. A baseline for high-precision detection of known terms

TODO (for model integration):
- [ ] Add Azure ML endpoint client in inference.py
- [ ] Load system prompt for LLM
- [ ] Implement hybrid detection (rules + LLM)
- [ ] Add confidence scores from model
=============================================================================
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional, Literal
import asyncio

router = APIRouter()


# =============================================================================
# Request/Response Models (matching Model Diagram: backend/app/schemas.py)
# =============================================================================

class AnalysisRequest(BaseModel):
    text: str = Field(..., min_length=1)
    language: Optional[Literal['en', 'he', 'auto']] = 'auto'
    private_mode: Optional[bool] = True


class Issue(BaseModel):
    span: str
    severity: Literal['outdated', 'biased', 'offensive', 'incorrect']
    type: str
    description: str
    suggestion: Optional[str] = None
    start: int
    end: int


class AnalysisResponse(BaseModel):
    original_text: str
    analysis_status: str
    issues_found: list[Issue]
    corrected_text: Optional[str] = None
    note: Optional[str] = None


# =============================================================================
# DEMO: Rule-Based Term Dictionary
# =============================================================================
# This is a PLACEHOLDER for demonstration purposes.
#
# In production, the fine-tuned LLM will:
# - Understand context (e.g., academic discussion vs. prejudiced framing)
# - Detect subtle biases not captured by keyword matching
# - Handle variations and misspellings
# - Provide context-aware suggestions
#
# These rules serve as:
# - High-precision detection for known problematic terms
# - Fallback when model is unavailable
# - Baseline comparison for model evaluation
# =============================================================================

TERM_RULES = [
    # English terms
    {
        "term": "homosexual",
        "severity": "outdated",
        "type": "Outdated Terminology",
        "description": "The term 'homosexual' is considered clinical and outdated. It has historically been used in pathologizing contexts.",
        "suggestion": "Use 'gay' or 'lesbian' depending on context, or 'LGBTQ+ person'",
    },
    {
        "term": "transsexual",
        "severity": "outdated",
        "type": "Outdated Terminology",
        "description": "The term 'transsexual' is outdated and often perceived as medicalizing. It focuses on medical transition rather than identity.",
        "suggestion": "Use 'transgender person' or 'trans person'",
    },
    {
        "term": "sexual preference",
        "severity": "incorrect",
        "type": "Incorrect Terminology",
        "description": "Sexual orientation is not a choice or preference. Using 'preference' implies it can be changed.",
        "suggestion": "Use 'sexual orientation'",
    },
    {
        "term": "born a man",
        "severity": "offensive",
        "type": "Invalidating Language",
        "description": "This phrase invalidates a person's gender identity and implies that assigned sex determines gender.",
        "suggestion": "Use 'assigned male at birth (AMAB)' if medically relevant",
    },
    {
        "term": "born a woman",
        "severity": "offensive",
        "type": "Invalidating Language",
        "description": "This phrase invalidates a person's gender identity and implies that assigned sex determines gender.",
        "suggestion": "Use 'assigned female at birth (AFAB)' if medically relevant",
    },
    {
        "term": "normal people",
        "severity": "biased",
        "type": "Biased Language",
        "description": "Using 'normal' to describe non-LGBTQ+ people implies that LGBTQ+ people are abnormal.",
        "suggestion": "Use 'cisgender' or 'heterosexual' if referring to those specific groups, or be more specific",
    },
    {
        "term": "the gays",
        "severity": "biased",
        "type": "Dehumanizing Language",
        "description": "Using 'the gays' as a noun can be dehumanizing and othering.",
        "suggestion": "Use 'gay people' or 'gay individuals'",
    },
    {
        "term": "lifestyle choice",
        "severity": "incorrect",
        "type": "Incorrect Framing",
        "description": "Being LGBTQ+ is not a lifestyle choice. This framing is often used to delegitimize LGBTQ+ identities.",
        "suggestion": "Remove or rephrase; sexual orientation and gender identity are not choices",
    },
    {
        "term": "gay lifestyle",
        "severity": "biased",
        "type": "Stereotyping",
        "description": "There is no single 'gay lifestyle.' This term promotes stereotypes and reduces diverse experiences to a monolith.",
        "suggestion": "Be specific about what you mean, or remove the phrase entirely",
    },
    {
        "term": "admitted to being gay",
        "severity": "biased",
        "type": "Stigmatizing Language",
        "description": "Using 'admitted' implies that being gay is something shameful to confess.",
        "suggestion": "Use 'came out as gay' or 'shared that they are gay'",
    },
    {
        "term": "sex change",
        "severity": "outdated",
        "type": "Outdated Terminology",
        "description": "The term 'sex change' is outdated and focuses narrowly on surgery.",
        "suggestion": "Use 'gender-affirming surgery' or 'transition' depending on context",
    },
    {
        "term": "transgenders",
        "severity": "offensive",
        "type": "Grammatically Incorrect",
        "description": "Using 'transgender' as a noun is grammatically incorrect and dehumanizing.",
        "suggestion": "Use 'transgender people' or 'transgender individuals'",
    },
    {
        "term": "transgendered",
        "severity": "incorrect",
        "type": "Incorrect Grammar",
        "description": "'Transgendered' is grammatically incorrect. Transgender is an adjective, not a verb.",
        "suggestion": "Use 'transgender' (e.g., 'transgender person')",
    },
    # Hebrew terms
    {
        "term": "הומוסקסואל",
        "severity": "outdated",
        "type": "מונח מיושן",
        "description": "המונח 'הומוסקסואל' נחשב קליני ומיושן. היסטורית שימש בהקשרים פתולוגיים.",
        "suggestion": "השתמשו ב'גיי', 'לסבית', או 'אדם מקהילת הלהט\"ב'",
    },
    {
        "term": "טרנסקסואל",
        "severity": "outdated",
        "type": "מונח מיושן",
        "description": "המונח 'טרנסקסואל' מיושן ונתפס כממדיקל. הוא מתמקד במעבר רפואי ולא בזהות.",
        "suggestion": "השתמשו ב'אדם טרנסג'נדר' או 'אדם טרנס'",
    },
    {
        "term": "העדפה מינית",
        "severity": "incorrect",
        "type": "מונח שגוי",
        "description": "נטייה מינית אינה בחירה או העדפה. שימוש ב'העדפה' מרמז שניתן לשנות אותה.",
        "suggestion": "השתמשו ב'נטייה מינית'",
    },
    {
        "term": "נולד גבר",
        "severity": "offensive",
        "type": "שפה פוגענית",
        "description": "ביטוי זה פוגע בזהות המגדרית של האדם ומרמז שהמין שהוקצה בלידה קובע את המגדר.",
        "suggestion": "השתמשו ב'הוקצה זכר בלידה' אם רלוונטי רפואית",
    },
    {
        "term": "נולדה אישה",
        "severity": "offensive",
        "type": "שפה פוגענית",
        "description": "ביטוי זה פוגע בזהות המגדרית של האדם ומרמז שהמין שהוקצה בלידה קובע את המגדר.",
        "suggestion": "השתמשו ב'הוקצתה נקבה בלידה' אם רלוונטי רפואית",
    },
    {
        "term": "אנשים נורמליים",
        "severity": "biased",
        "type": "שפה מוטה",
        "description": "שימוש ב'נורמלי' לתיאור אנשים שאינם מקהילת הלהט\"ב מרמז שאנשים מהקהילה אינם נורמליים.",
        "suggestion": "השתמשו ב'סיסג'נדר' או 'הטרוסקסואל' אם מתכוונים לקבוצות אלו",
    },
]


# =============================================================================
# DEMO: Rule-Based Detection Function
# =============================================================================

def find_issues(text: str) -> list[Issue]:
    """
    DEMO/PLACEHOLDER: Find problematic terms using simple keyword matching.

    This function will be replaced/augmented with LLM-based detection that:
    - Understands context and nuance
    - Detects implicit bias and framing issues
    - Handles Hebrew morphological variations

    Args:
        text: The input text to analyze

    Returns:
        List of Issue objects for each detected term
    """
    issues = []
    text_lower = text.lower()

    for rule in TERM_RULES:
        term = rule["term"]
        term_lower = term.lower()

        # Find all occurrences (case-insensitive)
        start = 0
        while True:
            idx = text_lower.find(term_lower, start)
            if idx == -1:
                break

            # Get the actual text from original (preserving case)
            actual_span = text[idx:idx + len(term)]

            issues.append(Issue(
                span=actual_span,
                severity=rule["severity"],
                type=rule["type"],
                description=rule["description"],
                suggestion=rule.get("suggestion"),
                start=idx,
                end=idx + len(term),
            ))

            start = idx + len(term)

    # Sort by position in text
    issues.sort(key=lambda x: x.start)
    return issues


# =============================================================================
# Main Analysis Endpoint
# =============================================================================

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_text(request: AnalysisRequest):
    """
    Analyze text for non-inclusive LGBTQ+ language.

    **CURRENT STATUS: DEMO MODE (Rule-Based Detection)**

    This endpoint currently uses keyword matching as a placeholder.
    Production version will use the fine-tuned suzume-llama-3-8B model
    deployed on Azure ML Online Endpoint.

    Args:
        request: AnalysisRequest containing:
            - text: The text to analyze
            - language: 'en', 'he', or 'auto' (default: 'auto')
            - private_mode: If True, text is not logged (default: True)

    Returns:
        AnalysisResponse containing:
            - original_text: The input text
            - analysis_status: 'Success' or error status
            - issues_found: List of detected issues with positions
            - note: Status message about detection mode

    TODO (Model Integration):
        1. Call Azure ML endpoint with text
        2. Parse LLM JSON response
        3. Merge with rule-based results for hybrid detection
        4. Add confidence scores
    """
    # Small delay to simulate processing (can be removed in production)
    await asyncio.sleep(0.3)

    # DEMO: Use rule-based detection
    # TODO: Replace/augment with LLM inference call
    issues = find_issues(request.text)

    return AnalysisResponse(
        original_text=request.text,
        analysis_status="Success",
        issues_found=issues,
        corrected_text=None,  # TODO: Generate with LLM
        note=f"DEMO MODE: Found {len(issues)} issue(s) using rule-based detection. LLM integration pending."
    )