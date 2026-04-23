"""
Feedback Router — thumbs up/down per analysis flag.

Accepts votes from the frontend for any flag shown in AnnotationSidePanel.
Persists to DB when available; always returns 200 so the UI never blocks.

Vote mapping:
  'up'   → feedback_type='helpful'
  'down' → feedback_type='false_positive'
"""

import logging
import time
from collections import defaultdict
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth.users import current_user_optional
from app.db import repository as repo
from fastapi import Depends
from app.db.models import User

# Simple in-memory rate limit: max 10 votes per IP per minute
_rate_store: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT = 10
_RATE_WINDOW = 60.0


def _check_rate_limit(ip: str) -> None:
    now = time.monotonic()
    timestamps = _rate_store[ip]
    _rate_store[ip] = [t for t in timestamps if now - t < _RATE_WINDOW]
    if len(_rate_store[ip]) >= _RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Too many feedback submissions")
    _rate_store[ip].append(now)

logger = logging.getLogger(__name__)

router = APIRouter()

_VOTE_TO_TYPE = {
    "up": "helpful",
    "down": "false_positive",
}


class FeedbackRequest(BaseModel):
    vote: str
    flagged_text: str = Field(..., max_length=500)
    severity: str = Field(..., max_length=50)
    start_idx: int
    end_idx: int
    finding_id: Optional[UUID] = None
    run_id: Optional[UUID] = None
    comment: Optional[str] = Field(None, max_length=1000)


class FeedbackResponse(BaseModel):
    success: bool


@router.post("", response_model=FeedbackResponse)
async def submit_feedback(
    request: Request,
    body: FeedbackRequest,
    current_user: Optional[User] = Depends(current_user_optional),
):
    """
    Record a thumbs-up or thumbs-down for a single analysis flag.

    Both authenticated users and guests can submit feedback.
    DB persistence fails silently — the response is always 200.
    """
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    if body.vote not in ("up", "down"):
        return FeedbackResponse(success=False)

    feedback_type = _VOTE_TO_TYPE[body.vote]
    user_id = current_user.id if current_user else None

    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        logger.debug("DB pool not available — feedback not persisted")
        return FeedbackResponse(success=True)

    try:
        async with pool.acquire(timeout=5.0) as conn:
            await repo.insert_feedback(
                conn=conn,
                feedback_type=feedback_type,
                vote=body.vote,
                run_id=body.run_id,
                finding_id=body.finding_id,
                user_id=user_id,
                flagged_text=body.flagged_text,
                severity=body.severity,
                start_idx=body.start_idx,
                end_idx=body.end_idx,
                comment=body.comment,
            )
        logger.info(
            "Feedback saved: vote=%s flagged_text=%r severity=%s user=%s",
            body.vote, body.flagged_text, body.severity, user_id or "guest",
        )
    except Exception as e:
        import asyncpg
        if isinstance(e, (asyncpg.UndefinedColumnError, asyncpg.NotNullViolationError,
                          asyncpg.CheckViolationError)):
            logger.warning(
                "Feedback not persisted — DB schema needs migration. "
                "Run: psql $DATABASE_URL -f db/migrations/001_feedback_columns.sql"
            )
        else:
            logger.exception("Feedback persistence failed — returning success anyway")

    return FeedbackResponse(success=True)
