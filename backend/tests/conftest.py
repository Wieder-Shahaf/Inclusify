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
