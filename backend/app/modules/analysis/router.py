"""
Analysis Router - LGBTQ+ Inclusive Language Detection

=============================================================================
                        HYBRID DETECTION (LLM + Rules)
=============================================================================
This module uses hybrid detection combining:
- LLM (lightblue/suzume-llama-3-8B-multilingual) for contextual analysis
- Rule-based detection as fallback for high-precision known terms

Detection modes (reported in analysis_mode field):
- "llm": All sentences successfully analyzed by LLM
- "hybrid": Some LLM success + some rule-based fallback
- "rules_only": LLM unavailable, using rule-based only

The rule-based approach serves as:
1. A fallback when the LLM endpoint is unavailable
2. A baseline for high-precision detection of known terms
3. Complementary detection for terms not in LLM training

DB persistence:
- When private_mode=False and DB is available, persists documents,
  analysis_runs, findings, and suggestions.
- When private_mode=True (default), runs entirely in-memory.
- DB failures never break analysis — results are always returned.

TODO (remaining):
- [x] Add confidence scores from model
=============================================================================
"""

import logging
import hashlib
import time

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, Literal

from app.auth.users import current_user_optional
from app.db.models import User
from app.db import repository as repo
from app.modules.analysis.call_metrics import CallMetrics
from app.modules.analysis.hybrid_detector import HybridDetector

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class AnalysisRequest(BaseModel):
    text: str = Field(..., min_length=1)
    language: Optional[Literal['en', 'he', 'auto']] = 'auto'
    private_mode: Optional[bool] = False 


class Issue(BaseModel):
    flagged_text: str
    severity: Literal['outdated', 'biased', 'potentially_offensive', 'factually_incorrect']
    type: str
    description: str
    suggestion: Optional[str] = None
    start: int
    end: int
    confidence: Optional[float] = None


class AnalysisResponse(BaseModel):
    original_text: str
    analysis_status: str
    issues_found: list[Issue]
    corrected_text: Optional[str] = None
    note: Optional[str] = None
    analysis_mode: Literal['llm', 'hybrid', 'rules_only'] = 'rules_only'


# =============================================================================
# Severity Mapping (API → DB)
# =============================================================================

_SEVERITY_TO_DB = {
    "potentially_offensive": "high",
    "biased": "medium",
    "factually_incorrect": "medium",
    "outdated": "low",
}


def _map_severity_to_db(api_severity: str) -> str:
    """Map API severity (outdated/biased/...) to DB severity (low/medium/high)."""
    return _SEVERITY_TO_DB.get(api_severity, "medium")


# =============================================================================
# Rule-Based Term Dictionary
# =============================================================================

INCLUSIVE_LANGUAGE_RULES = [
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
        "severity": "factually_incorrect",
        "type": "Incorrect Terminology",
        "description": "Sexual orientation is not a choice or preference. Using 'preference' implies it can be changed.",
        "suggestion": "Use 'sexual orientation'",
    },
    {
        "term": "born a man",
        "severity": "potentially_offensive",
        "type": "Invalidating Language",
        "description": "This phrase invalidates a person's gender identity and implies that assigned sex determines gender.",
        "suggestion": "Use 'assigned male at birth (AMAB)' if medically relevant",
    },
    {
        "term": "born a woman",
        "severity": "potentially_offensive",
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
        "severity": "factually_incorrect",
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
        "severity": "potentially_offensive",
        "type": "Grammatically Incorrect",
        "description": "Using 'transgender' as a noun is grammatically incorrect and dehumanizing.",
        "suggestion": "Use 'transgender people' or 'transgender individuals'",
    },
    {
        "term": "transgendered",
        "severity": "factually_incorrect",
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
        "severity": "factually_incorrect",
        "type": "מונח שגוי",
        "description": "נטייה מינית אינה בחירה או העדפה. שימוש ב'העדפה' מרמז שניתן לשנות אותה.",
        "suggestion": "השתמשו ב'נטייה מינית'",
    },
    {
        "term": "נולד גבר",
        "severity": "potentially_offensive",
        "type": "שפה פוגענית",
        "description": "ביטוי זה פוגע בזהות המגדרית של האדם ומרמז שהמין שהוקצה בלידה קובע את המגדר.",
        "suggestion": "השתמשו ב'הוקצה זכר בלידה' אם רלוונטי רפואית",
    },
    {
        "term": "נולדה אישה",
        "severity": "potentially_offensive",
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
# Rule-Based Detection Function
# =============================================================================

def detect_rule_based_issues(text: str) -> list[Issue]:
    """Detect problematic terms using rule-based keyword matching."""
    logger.info("Rule-based detection started: text_length=%d rules=%d", len(text), len(INCLUSIVE_LANGUAGE_RULES))
    start_time = time.monotonic()
    issues = []
    text_lower = text.lower()

    for rule in INCLUSIVE_LANGUAGE_RULES:
        term = rule["term"]
        term_lower = term.lower()

        start = 0
        while True:
            idx = text_lower.find(term_lower, start)
            if idx == -1:
                break

            actual_span = text[idx:idx + len(term)]

            issues.append(Issue(
                flagged_text=actual_span,
                severity=rule["severity"],
                type=rule["type"],
                description=rule["description"],
                suggestion=rule.get("suggestion"),
                start=idx,
                end=idx + len(term),
            ))

            start = idx + len(term)

    issues.sort(key=lambda x: x.start)
    elapsed = time.monotonic() - start_time
    logger.info("Rule-based detection completed: issues_found=%d elapsed_s=%.3f", len(issues), elapsed)
    return issues


# =============================================================================
# DB Persistence (non-private mode only)
# =============================================================================

# Allow user to be None for guest runs
async def _persist_results(
    request: Request,
    user: User | None,  # Changed this line to allow None
    text: str,
    language: str,
    private_mode: bool,
    analysis_mode: str,
    issues: list[Issue],
    runtime_ms: int,
) -> None:
    """Persist analysis results to DB. Fails silently — never breaks the response."""
    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        logger.debug("DB pool not available — skipping persistence")
        return

    text_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()

    try:
        async with pool.acquire(timeout=5.0) as conn:
            # 1. Create document and run FIRST (so they exist even if findings fail)
            doc_id = await repo.create_document(
                conn=conn,
                user_id=user.id if user else None,
                input_type="paste",
                language=language,
                private_mode=private_mode,
                mime_type="text/plain",
                text_storage_ref=None,
                text_sha256=text_sha256,
            )

            run_id = await repo.create_run(
                conn=conn,
                document_id=doc_id,
                model_version=f"hybrid-v1-{analysis_mode}",
                status="running",
                config_snapshot={
                    "mode": analysis_mode,
                    "language": language,
                    "private_mode": private_mode,
                },
            )

            # 2. Wrap ONLY the findings inserts in a transaction
            try:
                async with conn.transaction():
                    for iss in issues:
                        finding_id = await repo.insert_finding(
                            conn=conn,
                            run_id=run_id,
                            category=iss.type,
                            severity=_map_severity_to_db(iss.severity),
                            start_idx=iss.start,
                            end_idx=iss.end,
                            explanation=iss.description,
                            excerpt_redacted=iss.flagged_text,
                            confidence=iss.confidence,
                        )
                        if iss.suggestion:
                            await repo.insert_suggestion(
                                conn=conn,
                                finding_id=finding_id,
                                language=language if language in ("he", "en") else "he",
                                replacement_text=iss.suggestion,
                            )

                     # 3. If everything is good, mark as succeeded
                    await repo.finish_run(conn, run_id=run_id, status="succeeded", runtime_ms=runtime_ms)
                logger.info("DB persistence succeeded: user_id=%s issues=%d", user.id if user else "guest", len(issues))

            except Exception as inner_e:
                # 4. If findings fail, rollback happens, BUT we can mark the run as failed!
                await repo.finish_run(conn, run_id=run_id, status="failed", runtime_ms=runtime_ms, error_message=str(inner_e))
                logger.error("Findings insert failed. Run marked as failed.")

    except Exception:
        logger.exception("Complete DB persistence failure — analysis results were still returned to user")

# =============================================================================
# Metrics Persistence (always fires, privacy-safe — no text stored)
# =============================================================================

async def _persist_metrics(
    request: Request,
    call_metrics: CallMetrics,
    analysis_mode: str,
    runtime_ms: int,
) -> None:
    """Persist per-request vLLM performance metrics. Fails silently."""
    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        logger.debug("DB pool not available — skipping metrics persistence")
        return
    try:
        async with pool.acquire(timeout=5.0) as conn:
            await repo.insert_model_metric(
                conn,
                call_metrics.to_insert_dict(
                    analysis_mode=analysis_mode,
                    total_runtime_ms=runtime_ms,
                ),
            )
        logger.debug(
            "Metrics persisted: mode=%s llm_calls=%d errors=%d avg_latency_ms=%s",
            analysis_mode,
            call_metrics.llm_calls,
            call_metrics.llm_errors,
            f"{call_metrics.avg_latency_ms():.1f}" if call_metrics.avg_latency_ms() else "n/a",
        )
    except Exception:
        logger.exception("Metrics persistence failed — analysis results were still returned to user")


# =============================================================================
# Endpoint (Hybrid Detection + Optional DB Persistence)
# =============================================================================

_hybrid_detector = HybridDetector()


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_text(
    request: Request,
    body: AnalysisRequest,
    current_user: User | None = Depends(current_user_optional),
):
    """
    Analyze text for non-inclusive LGBTQ+ language.

    **Privacy mode** (default=False): Analysis runs in memory unless persistence is needed.
    When private_mode=False and user is authenticated, documents, runs,
    and findings are persisted to DB.

    Supports both authenticated users and guests (unauthenticated).
    - Authenticated: run is linked to user_id.
    - Guest: run is saved with user_id=NULL

    Uses hybrid detection (LLM + rule-based fallback).
    Response includes analysis_mode: "llm" | "hybrid" | "rules_only".

    """
    text_length = len(body.text)
    language = body.language or "auto"
    private_mode = body.private_mode if body.private_mode is not None else True
    user_id = current_user.id if current_user else "anonymous"
    logger.info(
        "Analysis started: user=%s text_length=%d language=%s private_mode=%s",
        user_id, text_length, language, private_mode,
    )

    start_time = time.monotonic()

    issues, analysis_mode, call_metrics = await _hybrid_detector.analyze(body.text, language=language)

    elapsed = time.monotonic() - start_time
    runtime_ms = int(elapsed * 1000)
    logger.info(
        "Analysis completed: issues_found=%d analysis_mode=%s elapsed_s=%.3f",
        len(issues), analysis_mode, elapsed,
    )

    # Persist full results to DB only when private_mode is off 
    if not private_mode :
        await _persist_results(
            request=request,
            user=current_user,
            text=body.text,
            language=language,
            private_mode=private_mode,
            analysis_mode=analysis_mode,
            issues=issues,
            runtime_ms=runtime_ms,
        )

    # Always persist model performance metrics (no text stored — privacy-safe)
    await _persist_metrics(
        request=request,
        call_metrics=call_metrics,
        analysis_mode=analysis_mode,
        runtime_ms=runtime_ms,
    )

    return AnalysisResponse(
        original_text=body.text,
        analysis_status="Success",
        issues_found=issues,
        corrected_text=None,
        note=f"Found {len(issues)} issue(s). Mode: {analysis_mode}",
        analysis_mode=analysis_mode,
    )
