"""Test admin endpoint returns 503 when DB pool is missing."""
import os

# Match env vars used by test_oauth.py so settings are consistent regardless of test import order.
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-testing-only")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///test_oauth.db")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.auth.deps import require_admin  # noqa: E402


async def _mock_require_admin():
    return {"email": "admin@test.com", "role": "site_admin"}


def test_admin_analytics_no_db():
    """Admin endpoint returns 503 when DB pool is missing."""
    client = TestClient(app)
    original_pool = getattr(app.state, "db_pool", None)
    app.dependency_overrides[require_admin] = _mock_require_admin
    app.state.db_pool = None
    try:
        response = client.get("/api/v1/admin/analytics")
        assert response.status_code == 503
        assert response.json()["detail"] == "Database not available"
    finally:
        app.dependency_overrides.clear()
        app.state.db_pool = original_pool
