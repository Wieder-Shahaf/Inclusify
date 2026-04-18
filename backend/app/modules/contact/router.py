"""Contact form router - sends email to site admins via smtplib.

No auth required: both authenticated and guest users may contact.
SMTP config via env vars: SMTP_HOST (default smtp.gmail.com),
SMTP_PORT (default 587, STARTTLS), SMTP_USER, SMTP_PASSWORD.
Gmail requires 2FA + App Password (not the account password).
"""
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_PDF_BYTES = 5 * 1024 * 1024  # 5 MB DoS mitigation


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
    sender_name: str = Form(default=""),
    sender_email: str = Form(default=""),
    sender_institution: str = Form(default=""),
    pdf_attachment: UploadFile = File(default=None),
):
    pdf_bytes = None
    if pdf_attachment is not None:
        pdf_bytes = await pdf_attachment.read()
        if len(pdf_bytes) > MAX_PDF_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"PDF attachment exceeds {MAX_PDF_BYTES} bytes",
            )

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

    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    if not smtp_user or not smtp_password:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SMTP credentials not configured",
        )

    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = ", ".join(admin_emails)
    msg["Subject"] = f"[Inclusify Contact] {subject}"
    body_text = (
        f"From: {sender_name or '(guest)'} <{sender_email or '(no email)'}>\n"
        f"Institution: {sender_institution or '(not provided)'}\n\n"
        f"{message}"
    )
    msg.attach(MIMEText(body_text, "plain", "utf-8"))

    if pdf_bytes:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(pdf_bytes)
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            'attachment; filename="analysis_report.pdf"',
        )
        msg.attach(part)

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, admin_emails, msg.as_string())
    except Exception as exc:
        logger.error("SMTP send failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Message could not be sent. Please try again later.",
        )

    return {"status": "sent"}
