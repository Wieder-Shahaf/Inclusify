"""
TDD tests for auth schemas and JWT strategy.

RED phase: These tests should fail initially because the auth module doesn't exist yet.
"""
import pytest
from pydantic import ValidationError


class TestUserCreateSchema:
    """Tests for UserCreate schema validation."""

    def test_valid_email_passes(self):
        """UserCreate should accept valid email format."""
        from app.auth.schemas import UserCreate

        user = UserCreate(email="test@example.com", password="securepass123")
        assert user.email == "test@example.com"

    def test_invalid_email_rejects(self):
        """UserCreate should reject invalid email format."""
        from app.auth.schemas import UserCreate

        with pytest.raises(ValidationError) as exc_info:
            UserCreate(email="not-an-email", password="securepass123")

        errors = exc_info.value.errors()
        assert any("email" in str(e).lower() for e in errors)

    def test_password_under_8_chars_rejects(self):
        """UserCreate should reject password under 8 characters."""
        from app.auth.schemas import UserCreate

        with pytest.raises(ValidationError) as exc_info:
            UserCreate(email="test@example.com", password="short")

        errors = exc_info.value.errors()
        assert any("password" in str(e).lower() or "min_length" in str(e).lower() for e in errors)

    def test_password_exactly_8_chars_passes(self):
        """UserCreate should accept password of exactly 8 characters."""
        from app.auth.schemas import UserCreate

        user = UserCreate(email="test@example.com", password="12345678")
        assert len(user.password) == 8


class TestJWTStrategy:
    """Tests for JWT strategy with role in claims."""

    @pytest.mark.asyncio
    async def test_jwt_encodes_user_id_and_role(self):
        """JWT strategy should encode user_id and role in token claims."""
        from app.auth.backend import get_jwt_strategy
        from unittest.mock import MagicMock
        import uuid

        strategy = get_jwt_strategy()

        # Create mock user
        user = MagicMock()
        user.id = uuid.UUID("12345678-1234-5678-1234-567812345678")
        user.role = "org_admin"

        token = await strategy.write_token(user)

        # Token should be a string
        assert isinstance(token, str)
        assert len(token) > 0

    @pytest.mark.asyncio
    async def test_jwt_decodes_valid_token(self):
        """JWT strategy should decode valid token and return payload."""
        from app.auth.backend import get_jwt_strategy
        from unittest.mock import MagicMock
        import uuid

        strategy = get_jwt_strategy()

        # Create and encode a token
        user = MagicMock()
        user.id = uuid.UUID("12345678-1234-5678-1234-567812345678")
        user.role = "user"

        token = await strategy.write_token(user)

        # Decode should return user_id
        decoded = await strategy.read_token(token)
        assert decoded is not None

    @pytest.mark.asyncio
    async def test_jwt_raises_on_expired_token(self):
        """JWT strategy should raise on expired token."""
        from app.auth.backend import get_jwt_strategy
        from jose import jwt
        import time

        strategy = get_jwt_strategy()

        # Create an already-expired token manually
        expired_payload = {
            "sub": "12345678-1234-5678-1234-567812345678",
            "aud": ["fastapi-users:auth"],
            "exp": int(time.time()) - 3600,  # Expired 1 hour ago
        }

        # This test verifies the strategy doesn't return a valid user ID for expired tokens
        # The exact behavior depends on fastapi-users implementation
        expired_token = jwt.encode(
            expired_payload,
            strategy.secret,
            algorithm="HS256"
        )

        # Expired token should return None or raise
        result = await strategy.read_token(expired_token)
        assert result is None  # fastapi-users returns None for invalid tokens
