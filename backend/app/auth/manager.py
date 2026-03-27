"""
User manager for FastAPI Users.

Handles user lifecycle events and password management.
"""
import logging
import uuid
from typing import Optional

import resend
from fastapi import Request
from fastapi_users import BaseUserManager, UUIDIDMixin

from app.db.models import User
from app.core.config import settings

logger = logging.getLogger(__name__)


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    """Custom user manager with logging and password validation."""

    reset_password_token_secret = settings.JWT_SECRET
    verification_token_secret = settings.JWT_SECRET

    async def on_after_register(
        self, user: User, request: Optional[Request] = None
    ) -> None:
        """Called after successful user registration."""
        logger.info(f"User {user.id} registered with email {user.email}")

    async def on_after_login(
        self,
        user: User,
        request: Optional[Request] = None,
        response=None,
    ) -> None:
        """Called after successful login."""
        logger.info(f"User {user.id} logged in")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ) -> None:
        """Called after password reset request. Sends reset email via Resend."""
        reset_url = f"{settings.FRONTEND_URL}/en/reset-password?token={token}"
        logger.info(f"Password reset requested for user {user.id} — RESET URL: {reset_url}")

        if not settings.RESEND_API_KEY:
            logger.warning("RESEND_API_KEY not set — skipping email send")
            return

        resend.api_key = settings.RESEND_API_KEY
        try:
            resend.Emails.send({
                "from": settings.EMAIL_FROM,
                "to": [user.email],
                "subject": "Reset your Inclusify password",
                "html": f"""
                    <div style="font-family:sans-serif;max-width:480px;margin:0 auto">
                        <h2 style="color:#7c3aed">Reset your password</h2>
                        <p>We received a request to reset your Inclusify password.</p>
                        <p style="margin:24px 0">
                            <a href="{reset_url}"
                               style="background:#7c3aed;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600">
                                Reset Password
                            </a>
                        </p>
                        <p style="color:#64748b;font-size:14px">
                            This link expires in 1 hour. If you didn't request a reset, ignore this email.
                        </p>
                    </div>
                """,
            })
            logger.info(f"Reset email sent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send reset email to {user.email}: {e}")

    async def on_after_reset_password(
        self, user: User, request: Optional[Request] = None
    ) -> None:
        """Called after successful password reset."""
        logger.info(f"Password reset completed for user {user.id}")


async def get_user_manager(user_db=None):
    """Dependency that provides UserManager instance.

    Note: user_db is injected by FastAPI Users dependency chain.
    """
    if user_db is None:
        raise RuntimeError("get_user_manager should be called via Depends()")

    yield UserManager(user_db)
