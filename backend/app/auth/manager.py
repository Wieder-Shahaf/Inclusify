"""
User manager for FastAPI Users.

Handles user lifecycle events and password management.
"""
import logging
import uuid
from typing import Optional

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
        """Called after password reset request."""
        logger.info(f"Password reset requested for user {user.id}")

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
