"""
History Router — Analysis History for Authenticated Users

Returns paginated analysis history ordered by most recent first.
Requires authentication. Returns 503 when the DB pool is unavailable.
"""

import json
import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.auth.users import current_active_user
from app.db.models import User
from app.db import repository as repo

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================

class HistoryItem(BaseModel):
    document_id: str
    run_id: str
    original_filename: Optional[str] = None
    language: str
    created_at: datetime
    input_type: str
    runtime_ms: Optional[int] = None
    total_findings: int
    high_count: int
    medium_count: int
    low_count: int
    score: Optional[int] = None
    word_count: Optional[int] = None
    analysis_mode: Optional[str] = None


class HistoryResponse(BaseModel):
    items: list[HistoryItem]
    total: int
    limit: int
    offset: int


# =============================================================================
# Endpoint
# =============================================================================

@router.get("/", response_model=HistoryResponse)
async def get_history(
    request: Request,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(current_active_user),
):
    """
    Return paginated analysis history for the authenticated user.

    Results are ordered by most recent first.
    Only non-private, succeeded analyses are included.
    """
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    if offset < 0:
        raise HTTPException(status_code=400, detail="offset must be >= 0")

    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        raise HTTPException(
            status_code=503,
            detail="History unavailable: no database connection",
        )

    try:
        async with pool.acquire(timeout=5.0) as conn:
            rows = await repo.get_user_history(conn, current_user.id, limit=limit, offset=offset)
            total = await repo.count_user_history(conn, current_user.id)
    except Exception:
        logger.exception("Failed to fetch user history for user_id=%s", current_user.id)
        raise HTTPException(status_code=500, detail="Failed to fetch history")

    items: list[HistoryItem] = []
    for r in rows:
        snapshot = r.get("config_snapshot") or {}
        if isinstance(snapshot, str):
            try:
                snapshot = json.loads(snapshot)
            except Exception:
                snapshot = {}

        items.append(HistoryItem(
            document_id=str(r["document_id"]),
            run_id=str(r["run_id"]),
            original_filename=r.get("original_filename"),
            language=r["language"],
            created_at=r["created_at"],
            input_type=r["input_type"],
            runtime_ms=r.get("runtime_ms"),
            total_findings=r["total_findings"],
            high_count=r["high_count"],
            medium_count=r["medium_count"],
            low_count=r["low_count"],
            score=snapshot.get("score"),
            word_count=snapshot.get("word_count"),
            analysis_mode=snapshot.get("mode"),
        ))

    logger.info(
        "History fetched: user_id=%s total=%d limit=%d offset=%d",
        current_user.id, total, limit, offset,
    )

    return HistoryResponse(items=items, total=total, limit=limit, offset=offset)
