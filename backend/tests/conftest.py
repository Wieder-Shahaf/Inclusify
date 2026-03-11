import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture
def mock_pool():
    """Create a mock asyncpg pool for testing without real DB"""
    pool = MagicMock()
    pool.get_size.return_value = 5
    pool.get_idle_size.return_value = 3
    pool.get_min_size.return_value = 2
    pool.get_max_size.return_value = 10

    # Mock connection context manager
    mock_conn = MagicMock()
    mock_conn.fetchval = AsyncMock(return_value=1)

    async_ctx = MagicMock()
    async_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    async_ctx.__aexit__ = AsyncMock(return_value=None)
    pool.acquire.return_value = async_ctx

    return pool


@pytest_asyncio.fixture
async def test_client(mock_pool):
    """Create test client with mocked DB pool"""
    from app.main import app

    # Inject mock pool
    app.state.db_pool = mock_pool

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# vLLM mock fixtures for Phase 03 LLM integration tests
@pytest.fixture
def mock_vllm_response():
    """Mock successful vLLM chat completions response."""
    return {
        "id": "test-id",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "inclusify",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": '{"category": "Pathologizing Language", "severity": "Biased", "explanation": "Test explanation"}'
            },
            "finish_reason": "stop"
        }],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
    }


@pytest.fixture
def mock_vllm_timeout_response():
    """Mock vLLM timeout scenario."""
    import httpx
    return httpx.TimeoutException("Connection timed out")


@pytest.fixture
def sample_text_english():
    """Sample English text for testing."""
    return "The homosexual lifestyle is a choice. Gender identity disorder requires treatment."


@pytest.fixture
def sample_text_hebrew():
    """Sample Hebrew text for testing."""
    return "הומוסקסואליות היא מחלה. סטיית מין דורשת טיפול."


# Google OAuth mock fixtures for Phase 05.5
@pytest.fixture
def mock_google_oauth_response():
    """Mock successful Google OAuth token exchange response."""
    return {
        "access_token": "mock-google-access-token",
        "token_type": "Bearer",
        "expires_in": 3600,
        "id_token": "mock-id-token",
    }


@pytest.fixture
def mock_google_user_info():
    """Mock Google user info response (from id_token or userinfo endpoint)."""
    return {
        "sub": "google-user-id-12345",
        "email": "oauthuser@gmail.com",
        "email_verified": True,
        "name": "OAuth Test User",
        "picture": "https://example.com/photo.jpg",
    }


@pytest.fixture
def mock_google_oauth_error():
    """Mock Google OAuth error response."""
    return {
        "error": "access_denied",
        "error_description": "User denied access",
    }
