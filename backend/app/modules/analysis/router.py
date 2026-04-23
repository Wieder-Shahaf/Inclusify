"""
Analysis Router - LGBTQ+ Inclusive Language Detection

=============================================================================
                        LLM-BASED DETECTION
=============================================================================
This module uses LLM-based contextual analysis only.

Detection modes (reported in analysis_mode field):
- "llm": LLM analysis completed (full or partial sentence coverage)
- "rules_only": LLM unavailable — no issues returned

DB persistence:
- When private_mode=False and DB is available, persists documents,
  analysis_runs, findings, and suggestions.
- When private_mode=True (default), runs entirely in-memory.
- DB failures never break analysis — results are always returned.
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
from app.modules.analysis.hybrid_detector import HybridDetector, detect_language
from app.modules.admin.router import ws_manager
from app.core.blob_storage import upload_text as _blob_upload_text

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class AnalysisRequest(BaseModel):
    text: str = Field(..., min_length=1)
    language: Optional[Literal['en', 'he', 'auto']] = 'auto'
    private_mode: Optional[bool] = False
    input_type: Optional[Literal['pdf', 'docx', 'pptx', 'txt']] = None
    original_filename: Optional[str] = None
    mime_type: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    page_count: Optional[int] = None
    detected_language: Optional[Literal['he', 'en']] = None
    file_storage_ref: Optional[str] = None
    chunks: Optional[list[str]] = None


class Issue(BaseModel):
    flagged_text: str
    severity: Literal['outdated', 'biased', 'potentially_offensive', 'factually_incorrect']
    type: str
    description: str
    suggestion: Optional[str] = None
    inclusive_sentence: Optional[str] = None
    phrase: Optional[str] = None
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
    run_id: Optional[str] = None


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
# DB Persistence (non-private mode only)
# =============================================================================

# Allow user to be None for guest runs
async def _persist_results(
    request: Request,
    user: Optional[User],
    text: str,
    language: str,
    private_mode: bool,
    analysis_mode: str,
    issues: list[Issue],
    runtime_ms: int,
    input_type: Optional[str] = None,
    original_filename: Optional[str] = None,
    mime_type: Optional[str] = None,
    title: Optional[str] = None,
    author: Optional[str] = None,
    page_count: Optional[int] = None,
    detected_language: Optional[str] = None,
    text_storage_ref: Optional[str] = None,
) -> Optional[str]:
    """Persist analysis results to DB. Returns run_id on success, None otherwise."""
    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        logger.debug("DB pool not available — skipping persistence")
        return None

    text_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()

    try:
        async with pool.acquire(timeout=5.0) as conn:
            # 1. Create document and run FIRST (so they exist even if findings fail)
            doc_id = await repo.create_document(
                conn=conn,
                user_id=user.id if user else None,
                input_type=input_type,
                language=language,
                private_mode=private_mode,
                mime_type=mime_type or "text/plain",
                original_filename=original_filename,
                text_storage_ref=text_storage_ref,
                text_sha256=text_sha256,
                title=title,
                author=author,
                page_count=page_count,
                detected_language=detected_language,
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
                            excerpt_redacted=iss.phrase or iss.flagged_text,
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

            return str(run_id)

    except Exception:
        logger.exception("Complete DB persistence failure — analysis results were still returned to user")
        return None

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
    current_user: Optional[User] = Depends(current_user_optional),
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
    private_mode = body.private_mode if body.private_mode is not None else False
    user_id = current_user.id if current_user else "anonymous"

    # Resolve detected_language: prefer explicit value from upload pipeline,
    # fall back to auto-detecting from text when language is "auto".
    if body.detected_language:
        detected_language = body.detected_language
    elif language != "auto":
        detected_language = language
    else:
        detected_language = detect_language(body.text)

    logger.info(
        "Analysis started: user=%s text_length=%d language=%s detected_language=%s private_mode=%s",
        user_id, text_length, language, detected_language, private_mode,
    )

    start_time = time.monotonic()

    issues, analysis_mode, call_metrics = await _hybrid_detector.analyze(body.text, language=language, chunks=body.chunks)

    elapsed = time.monotonic() - start_time
    runtime_ms = int(elapsed * 1000)
    logger.info(
        "Analysis completed: issues_found=%d analysis_mode=%s elapsed_s=%.3f",
        len(issues), analysis_mode, elapsed,
    )

    persisted_run_id: Optional[str] = None
    # Persist full results to DB only when private_mode is off
    if not private_mode:
        if current_user is None:
            logger.warning(
                "Analysis saved as GUEST (user_id=NULL) — run will NOT appear in history. "
                "User must be logged in for history tracking."
            )
        text_sha256 = hashlib.sha256(body.text.encode("utf-8")).hexdigest()
        text_storage_ref = await _blob_upload_text(text_sha256, body.text)

        # Map client input_type ('pdf','docx','pptx','txt') → DB enum ('paste'|'upload')
        db_input_type = "upload" if body.input_type and body.input_type != "paste" else "paste"

        persisted_run_id = await _persist_results(
            request=request,
            user=current_user,
            text=body.text,
            language=language,
            private_mode=private_mode,
            analysis_mode=analysis_mode,
            issues=issues,
            runtime_ms=runtime_ms,
            input_type=db_input_type,
            original_filename=body.original_filename,
            mime_type=body.mime_type,
            title=body.title,
            author=body.author,
            page_count=body.page_count,
            detected_language=detected_language,
            text_storage_ref=text_storage_ref,
        )
        try:
            await ws_manager.broadcast({"event": "new_analysis"})
        except Exception:
            # Broadcast failures must not fail the analysis request
            pass

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
        run_id=persisted_run_id if not private_mode else None,
    )
