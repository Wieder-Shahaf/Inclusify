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

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import MagicMock, AsyncMock, patch

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


class TestGoogleOAuthAuthorize:
    """Tests for /auth/google/authorize endpoint."""

    @pytest.mark.asyncio
    async def test_authorize_redirects(self, mock_db_pool, mock_redis):
        """GET /auth/google/authorize redirects to Google consent screen."""
        # This test will be implemented when the endpoint exists
        # For now, it's a stub that passes (Wave 0)
        pytest.skip("Endpoint not yet implemented - Wave 0 stub")


class TestGoogleOAuthCallback:
    """Tests for /auth/google/callback endpoint."""

    @pytest.mark.asyncio
    async def test_callback_creates_user(self, mock_db_pool, mock_redis):
        """GET /auth/google/callback with valid code creates user and redirects with token."""
        pytest.skip("Endpoint not yet implemented - Wave 0 stub")

    @pytest.mark.asyncio
    async def test_oauth_jwt_has_role(self, mock_db_pool, mock_redis):
        """OAuth-generated JWT includes role claim like password login."""
        pytest.skip("Endpoint not yet implemented - Wave 0 stub")

    @pytest.mark.asyncio
    async def test_associate_by_email(self, mock_db_pool, mock_redis):
        """OAuth links to existing account with matching email."""
        pytest.skip("Endpoint not yet implemented - Wave 0 stub")

    @pytest.mark.asyncio
    async def test_error_redirect(self, mock_db_pool, mock_redis):
        """OAuth error redirects to frontend with error param."""
        pytest.skip("Endpoint not yet implemented - Wave 0 stub")

    @pytest.mark.asyncio
    async def test_state_validation(self, mock_db_pool, mock_redis):
        """Invalid CSRF state is rejected."""
        pytest.skip("Endpoint not yet implemented - Wave 0 stub")


# Cleanup test database after module
def teardown_module():
    import os
    if os.path.exists("test_oauth.db"):
        os.remove("test_oauth.db")
