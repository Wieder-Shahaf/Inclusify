"""
Tests for forgot-password and reset-password endpoints.

Covers:
- Forgot password for valid email/password user
- Forgot password for nonexistent email → 404
- Forgot password for Google OAuth user → 400
- Reset password with valid token
- Reset password with invalid token → 400
"""
import os

os.environ["JWT_SECRET"] = "test-secret-key-for-testing-only"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test_password_reset.db"
os.environ["RESEND_API_KEY"] = ""  # Disable email sending in tests

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import MagicMock, AsyncMock, patch

pytest_plugins = ("pytest_asyncio",)


@pytest.fixture
def mock_db_pool():
    pool = MagicMock()
    pool.get_size.return_value = 5
    pool.get_idle_size.return_value = 3
    pool.get_min_size.return_value = 2
    pool.get_max_size.return_value = 10

    mock_conn = MagicMock()
    mock_conn.fetchval = AsyncMock(return_value=1)

    async_ctx = MagicMock()
    async_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    async_ctx.__aexit__ = AsyncMock(return_value=None)
    pool.acquire.return_value = async_ctx
    pool.close = AsyncMock()

    return pool


@pytest.fixture
def mock_redis():
    redis_manager = MagicMock()
    redis_manager.store_refresh_token = AsyncMock()
    redis_manager.validate_refresh_token = AsyncMock(return_value=True)
    redis_manager.invalidate_refresh_token = AsyncMock()
    redis_manager.close = AsyncMock()
    return redis_manager


@pytest_asyncio.fixture
async def test_client(mock_db_pool, mock_redis):
    import app.core.redis as redis_module
    import app.db.connection as connection_module

    with patch.object(redis_module, "init_redis", return_value=mock_redis), patch.object(
        redis_module, "close_redis"
    ), patch.object(connection_module, "create_pool", return_value=mock_db_pool):
        from app.main import app
        from app.auth.users import create_db_and_tables

        await create_db_and_tables()

        app.state.db_pool = mock_db_pool
        app.state.redis = mock_redis

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    if os.path.exists("test_password_reset.db"):
        os.remove("test_password_reset.db")


async def register_user(client, email="resetuser@example.com", password="testpass123"):
    """Helper to register a user and return the response."""
    return await client.post(
        "/auth/jwt/register",
        json={"email": email, "password": password},
    )


class TestForgotPassword:
    """Tests for POST /auth/jwt/forgot-password."""

    @pytest.mark.asyncio
    async def test_forgot_password_valid_user(self, test_client):
        """Forgot password for registered email/password user returns 200."""
        await register_user(test_client, email="forgot@example.com")

        response = await test_client.post(
            "/auth/jwt/forgot-password",
            json={"email": "forgot@example.com"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_forgot_password_nonexistent_email(self, test_client):
        """Forgot password for unknown email returns 404 EMAIL_NOT_FOUND."""
        response = await test_client.post(
            "/auth/jwt/forgot-password",
            json={"email": "nobody@example.com"},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "EMAIL_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_forgot_password_invalid_email_format(self, test_client):
        """Forgot password with invalid email format returns 422."""
        response = await test_client.post(
            "/auth/jwt/forgot-password",
            json={"email": "not-an-email"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_forgot_password_oauth_user(self, test_client):
        """Forgot password for OAuth user returns 400 OAUTH_USER."""
        # Register a normal user first, then simulate OAuth by adding an oauth_account
        await register_user(test_client, email="googleuser@example.com")

        # Add OAuth account directly via SQLAlchemy
        from app.auth.users import async_session_maker
        from app.db.models import User, OAuthAccount
        from sqlalchemy import select
        import uuid

        async with async_session_maker() as session:
            result = await session.execute(
                select(User).where(User.email == "googleuser@example.com")
            )
            user = result.unique().scalar_one()

            oauth_account = OAuthAccount(
                id=uuid.uuid4(),
                user_id=user.id,
                oauth_name="google",
                access_token="mock-token",
                account_id="google-123",
                account_email="googleuser@example.com",
            )
            session.add(oauth_account)
            await session.commit()

        response = await test_client.post(
            "/auth/jwt/forgot-password",
            json={"email": "googleuser@example.com"},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "OAUTH_USER"


class TestResetPassword:
    """Tests for POST /auth/jwt/reset-password."""

    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(self, test_client):
        """Reset password with invalid token returns 400."""
        response = await test_client.post(
            "/auth/jwt/reset-password",
            json={"token": "invalid-token-xyz", "password": "newpass123"},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "RESET_PASSWORD_BAD_TOKEN"

    @pytest.mark.asyncio
    async def test_reset_password_full_flow(self, test_client):
        """Full flow: register → forgot password → capture token → reset → login with new password."""
        await register_user(test_client, email="fullflow@example.com", password="oldpass123")

        # Capture the token from the manager callback
        captured_token = {}

        from app.auth.manager import UserManager

        async def capture_token(self, user, token, request=None):
            captured_token["token"] = token

        with patch.object(UserManager, "on_after_forgot_password", capture_token):
            response = await test_client.post(
                "/auth/jwt/forgot-password",
                json={"email": "fullflow@example.com"},
            )
            assert response.status_code == 200

        assert "token" in captured_token

        # Reset password with captured token
        response = await test_client.post(
            "/auth/jwt/reset-password",
            json={"token": captured_token["token"], "password": "newpass456"},
        )
        assert response.status_code == 200

        # Login with new password should succeed
        response = await test_client.post(
            "/auth/jwt/login",
            data={"username": "fullflow@example.com", "password": "newpass456"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

        # Login with old password should fail
        response = await test_client.post(
            "/auth/jwt/login",
            data={"username": "fullflow@example.com", "password": "oldpass123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 400
