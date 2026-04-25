"""
Integration tests for authentication endpoints.

Tests the full auth flow: register, login, protected routes.
Uses SQLite in-memory database for isolation.
"""
import os

# Override settings before importing app modules
os.environ["JWT_SECRET"] = "test-secret"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test_auth.db"

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import MagicMock, AsyncMock, patch

# Configure pytest-asyncio
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


@pytest_asyncio.fixture
async def test_client(mock_db_pool, mock_redis):
    """Create test client with mocked dependencies."""
    # Import modules here to ensure env vars are set
    import app.core.redis as redis_module
    import app.db.connection as connection_module

    # Patch at module level
    with patch.object(redis_module, "init_redis", return_value=mock_redis), patch.object(
        redis_module, "close_redis"
    ), patch.object(connection_module, "create_pool", return_value=mock_db_pool):
        # Import app after patches are in place
        from app.main import app
        from app.auth.users import create_db_and_tables, engine
        from app.db.models import Base

        # Drop all auth tables first so each test starts with a clean DB,
        # regardless of which SQLite file the cached engine is pointing at.
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await create_db_and_tables()

        app.state.db_pool = mock_db_pool
        app.state.redis = mock_redis

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


class TestAuthRegister:
    """Tests for user registration endpoint."""

    @pytest.mark.asyncio
    async def test_register_creates_user(self, test_client):
        """POST /auth/jwt/register creates user and returns 201."""
        response = await test_client.post(
            "/auth/jwt/register",
            json={
                "email": "newuser@example.com",
                "password": "securepass123",
            },
        )

        # Should succeed (201 Created)
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert "id" in data
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_register_invalid_email_fails(self, test_client):
        """POST /auth/jwt/register with invalid email returns 422."""
        response = await test_client.post(
            "/auth/jwt/register",
            json={
                "email": "not-an-email",
                "password": "securepass123",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_short_password_fails(self, test_client):
        """POST /auth/jwt/register with short password returns 422."""
        response = await test_client.post(
            "/auth/jwt/register",
            json={
                "email": "test@example.com",
                "password": "short",
            },
        )

        assert response.status_code == 422


class TestAuthLogin:
    """Tests for login endpoint."""

    @pytest.mark.asyncio
    async def test_login_valid_credentials(self, test_client):
        """POST /auth/jwt/login with valid creds returns access_token."""
        # First register a user
        await test_client.post(
            "/auth/jwt/register",
            json={
                "email": "logintest@example.com",
                "password": "testpass123",
            },
        )

        # Then login
        response = await test_client.post(
            "/auth/jwt/login",
            data={
                "username": "logintest@example.com",
                "password": "testpass123",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_invalid_password(self, test_client):
        """POST /auth/jwt/login with wrong password returns 400."""
        # Register user
        await test_client.post(
            "/auth/jwt/register",
            json={
                "email": "wrongpass@example.com",
                "password": "correctpass123",
            },
        )

        # Try login with wrong password
        response = await test_client.post(
            "/auth/jwt/login",
            data={
                "username": "wrongpass@example.com",
                "password": "wrongpassword",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert response.status_code == 400


class TestProtectedRoutes:
    """Tests for protected route access."""

    @pytest.mark.asyncio
    async def test_users_me_with_token(self, test_client):
        """GET /users/me with valid token returns user info."""
        # Register and login
        await test_client.post(
            "/auth/jwt/register",
            json={
                "email": "metest@example.com",
                "password": "testpass123",
            },
        )

        login_response = await test_client.post(
            "/auth/jwt/login",
            data={
                "username": "metest@example.com",
                "password": "testpass123",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        token = login_response.json()["access_token"]

        # Access protected route
        response = await test_client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "metest@example.com"

    @pytest.mark.asyncio
    async def test_users_me_without_token(self, test_client):
        """GET /users/me without token returns 401."""
        response = await test_client.get("/users/me")

        assert response.status_code == 401
