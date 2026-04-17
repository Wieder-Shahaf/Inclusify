"""Test admin endpoint returns 503 when DB pool is missing.

Imports are done lazily inside the test to avoid triggering the Settings()
cache during module collection — that would freeze JWT_SECRET to whatever
env was set at collection time, breaking other tests (e.g. test_oauth) that
rely on their own env overrides.
"""


def test_admin_analytics_no_db():
    """Admin endpoint returns 503 when DB pool is missing."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.auth.deps import require_admin

    async def _mock_require_admin():
        return {"email": "admin@test.com", "role": "site_admin"}

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
