"""Contact form router - sends email to site admins via the Resend HTTP API.

Auth required: guests cannot contact. The sender identity (email, name,
institution) is taken from the authenticated user, not from client input.
Config via env vars: RESEND_API_KEY (required), RESEND_FROM (sender, must be a
Resend-verified domain; defaults to onboarding@resend.dev for testing).
SMTP is not used: Railway blocks outbound SMTP ports, so mail goes over HTTPS.
"""
import base64
import logging
import os
import time
from collections import defaultdict

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status

from app.auth.users import current_active_user
from app.db.models import User

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_PDF_BYTES = 5 * 1024 * 1024  # 5 MB DoS mitigation

# Anti-spam: max 5 contact messages per IP per hour. Mirrors feedback router.
# ponytail: in-memory + per-process — resets on restart, not shared across
# replicas. Fine at current single-container scale; swap for Redis if we scale out.
_rate_store: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT = 5
_RATE_WINDOW = 3600.0


def _check_rate_limit(ip: str) -> None:
    now = time.monotonic()
    _rate_store[ip] = [t for t in _rate_store[ip] if now - t < _RATE_WINDOW]
    if len(_rate_store[ip]) >= _RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many messages. Please try again later.",
        )
    _rate_store[ip].append(now)


def _pool(request: Request):
    if not getattr(request.app.state, "db_pool", None):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not available",
        )
    return request.app.state.db_pool


@router.post("", status_code=200)
async def send_contact(
    request: Request,
    subject: str = Form(..., min_length=1, max_length=300),
    message: str = Form(..., min_length=1, max_length=5000),
    pdf_attachment: UploadFile = File(default=None),
    current_user: User = Depends(current_active_user),
):
    # Sender identity comes from the authenticated user, never client input.
    sender_name = current_user.full_name or ""
    sender_email = current_user.email
    sender_institution = current_user.institution or ""

    # Rate-limit per user (falls back to IP if the client is somehow unknown).
    _check_rate_limit(str(current_user.id))

    pdf_bytes = None
    if pdf_attachment is not None:
        pdf_bytes = await pdf_attachment.read()
        if len(pdf_bytes) > MAX_PDF_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"PDF attachment exceeds {MAX_PDF_BYTES} bytes",
            )

    # Recipients: explicit CONTACT_RECIPIENTS (comma-separated) wins; otherwise
    # fall back to whoever holds site_admin so the form still works if unset.
    recipients_env = os.getenv("CONTACT_RECIPIENTS", "")
    admin_emails = [e.strip() for e in recipients_env.split(",") if e.strip()]
    if not admin_emails:
        pool = _pool(request)
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT email FROM users WHERE role = 'site_admin'"
            )
        admin_emails = [r["email"] for r in rows if r["email"]]
    if not admin_emails:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No admin recipients configured",
        )

    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email API key not configured",
        )
    from_addr = os.getenv("RESEND_FROM", "Inclusify <onboarding@resend.dev>")

    body_text = (
        f"From: {sender_name or '(guest)'} <{sender_email or '(no email)'}>\n"
        f"Institution: {sender_institution or '(not provided)'}\n\n"
        f"{message}"
    )
    payload = {
        "from": from_addr,
        "to": admin_emails,
        "subject": f"[Inclusify Contact] {subject}",
        "text": body_text,
    }
    # Let admins hit Reply and reach the sender directly, not the shared inbox.
    if sender_email:
        payload["reply_to"] = sender_email
    if pdf_bytes:
        payload["attachments"] = [{
            "filename": "analysis_report.pdf",
            "content": base64.b64encode(pdf_bytes).decode("ascii"),
        }]

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
            resp.raise_for_status()
    except Exception as exc:
        logger.error("Resend send failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Message could not be sent. Please try again later.",
        )

    return {"status": "sent"}
