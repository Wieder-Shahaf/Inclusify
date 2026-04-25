"""
Integration tests for Google OAuth endpoints.

Tests the OAuth flow: authorize redirect, callback, account linking.
Uses SQLite in-memory database and mocked Google OAuth responses.
"""
import os

# Override settings before importing app modules
os.environ["JWT_SECRET"] = "test-secret-key-for-testing-only"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test_oauth.db"
os.environ["GOOGLE_CLIENT_ID"] = "test-client-id"
os.environ["GOOGLE_CLIENT_SECRET"] = "test-client-secret"
os.environ["FRONTEND_URL"] = "http://localhost:3000"

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import MagicMock, AsyncMock, patch
from httpx_oauth.oauth2 import OAuth2Token

pytest_plugins = ("pytest_asyncio",)


@pytest.fixture
def mock_db_pool():
    """Mock asyncpg pool for tests."""
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
    """Mock Redis manager for tests."""
    redis_manager = MagicMock()
    redis_manager.store_refresh_token = AsyncMock()
    redis_manager.validate_refresh_token = AsyncMock(return_value=True)
    redis_manager.invalidate_refresh_token = AsyncMock()
    redis_manager.close = AsyncMock()
    return redis_manager


@pytest.fixture
def mock_google_token():
    """Mock Google OAuth token response."""
    return OAuth2Token({
        "access_token": "mock-access-token",
        "token_type": "Bearer",
        "expires_in": 3600,
    })


@pytest.fixture
def mock_google_userinfo():
    """Mock Google userinfo response."""
    return {
        "sub": "google-12345",
        "email": "testuser@gmail.com",
        "email_verified": True,
        "name": "Test User",
        "picture": "https://example.com/photo.jpg",
    }


@pytest_asyncio.fixture
async def test_client(mock_db_pool, mock_redis):
    """Create test client with mocked dependencies."""
    import app.core.redis as redis_module
    import app.db.connection as connection_module

    with patch.object(redis_module, "init_redis", return_value=mock_redis), \
         patch.object(redis_module, "close_redis"), \
         patch.object(connection_module, "create_pool", return_value=mock_db_pool):
        from app.main import app
        from app.auth.users import create_db_and_tables

        await create_db_and_tables()

        app.state.db_pool = mock_db_pool
        app.state.redis = mock_redis

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    # Clean up test database
    if os.path.exists("test_oauth.db"):
        os.remove("test_oauth.db")


class TestGoogleOAuthAuthorize:
    """Tests for /auth/google/authorize endpoint."""

    @pytest.mark.asyncio
    async def test_authorize_redirects(self, test_client):
        """GET /auth/google/authorize redirects to Google consent screen."""
        response = await test_client.get(
            "/auth/google/authorize",
            follow_redirects=False,
        )

        # Should redirect (302)
        assert response.status_code == 302

        # Should redirect to Google
        location = response.headers.get("location", "")
        assert "accounts.google.com" in location or "googleapis.com" in location


class TestGoogleOAuthCallback:
    """Tests for /auth/google/callback endpoint."""

    @pytest.mark.asyncio
    async def test_callback_creates_user(
        self, test_client, mock_google_token, mock_google_userinfo
    ):
        """GET /auth/google/callback with valid code creates user and redirects with token."""
        with patch("app.auth.oauth.google_oauth_client.get_access_token", new_callable=AsyncMock) as mock_get_token, \
             patch("app.auth.oauth.google_oauth_client.get_httpx_client") as mock_client_ctx:

            mock_get_token.return_value = mock_google_token

            # Mock the httpx client context manager and response
            mock_http_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = mock_google_userinfo
            mock_response.raise_for_status = MagicMock()
            mock_http_client.get = AsyncMock(return_value=mock_response)

            mock_client_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_http_client)
            mock_client_ctx.return_value.__aexit__ = AsyncMock(return_value=None)

            response = await test_client.get(
                "/auth/google/callback?code=mock-auth-code",
                follow_redirects=False,
            )

            # Should redirect to frontend
            assert response.status_code == 302
            location = response.headers.get("location", "")
            assert "localhost:3000" in location
            assert "access_token=" in location

    @pytest.mark.asyncio
    async def test_oauth_jwt_has_role(
        self, test_client, mock_google_token, mock_google_userinfo
    ):
        """OAuth-generated JWT includes role claim like password login."""
        with patch("app.auth.oauth.google_oauth_client.get_access_token", new_callable=AsyncMock) as mock_get_token, \
             patch("app.auth.oauth.google_oauth_client.get_httpx_client") as mock_client_ctx:

            mock_get_token.return_value = mock_google_token

            mock_http_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = mock_google_userinfo
            mock_response.raise_for_status = MagicMock()
            mock_http_client.get = AsyncMock(return_value=mock_response)

            mock_client_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_http_client)
            mock_client_ctx.return_value.__aexit__ = AsyncMock(return_value=None)

            response = await test_client.get(
                "/auth/google/callback?code=mock-auth-code",
                follow_redirects=False,
            )

            location = response.headers.get("location", "")
            # Extract token from URL
            import urllib.parse
            parsed = urllib.parse.urlparse(location)
            params = urllib.parse.parse_qs(parsed.query)

            assert "access_token" in params
            token = params["access_token"][0]

            # Decode and verify role claim — use the actual cached settings secret,
            # which may differ from JWT_SECRET env var if config was loaded earlier in the suite.
            from jose import jwt
            from app.core.config import settings
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"], audience="fastapi-users:auth")
            assert "role" in payload
            assert payload["role"] == "user"

    @pytest.mark.asyncio
    async def test_associate_by_email(
        self, test_client, mock_google_token, mock_google_userinfo
    ):
        """OAuth links to existing account with matching email."""
        # First create a user via password registration
        await test_client.post(
            "/auth/jwt/register",
            json={
                "email": "testuser@gmail.com",  # Same as mock_google_userinfo
                "password": "testpass123",
            },
        )

        with patch("app.auth.oauth.google_oauth_client.get_access_token", new_callable=AsyncMock) as mock_get_token, \
             patch("app.auth.oauth.google_oauth_client.get_httpx_client") as mock_client_ctx:

            mock_get_token.return_value = mock_google_token

            mock_http_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = mock_google_userinfo
            mock_response.raise_for_status = MagicMock()
            mock_http_client.get = AsyncMock(return_value=mock_response)

            mock_client_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_http_client)
            mock_client_ctx.return_value.__aexit__ = AsyncMock(return_value=None)

            response = await test_client.get(
                "/auth/google/callback?code=mock-auth-code",
                follow_redirects=False,
            )

            # Should still succeed (account linked)
            assert response.status_code == 302
            location = response.headers.get("location", "")
            assert "access_token=" in location

    @pytest.mark.asyncio
    async def test_error_redirect(self, test_client):
        """OAuth error redirects to frontend with error param."""
        response = await test_client.get(
            "/auth/google/callback?error=access_denied&error_description=User%20denied",
            follow_redirects=False,
        )

        assert response.status_code == 302
        location = response.headers.get("location", "")
        assert "localhost:3000" in location
        assert "error=access_denied" in location

    @pytest.mark.asyncio
    async def test_state_validation(self, test_client):
        """Missing code returns error."""
        response = await test_client.get(
            "/auth/google/callback",  # No code or error
            follow_redirects=False,
        )

        assert response.status_code == 302
        location = response.headers.get("location", "")
        assert "error=" in location


# Cleanup test database after module
def teardown_module():
    import os
    if os.path.exists("test_oauth.db"):
        os.remove("test_oauth.db")
