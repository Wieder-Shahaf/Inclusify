import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth.deps import require_admin

client = TestClient(app)

# פונקציה שמדמה אדמין מאושר
async def mock_require_admin():
    return {"email": "admin@test.com", "role": "site_admin"}

def test_admin_analytics_no_db():
    """Test that admin endpoint returns 503 when DB pool is missing."""
    # 1. עוקפים את מנגנון האבטחה לצורך הבדיקה
    app.dependency_overrides[require_admin] = mock_require_admin
    
    # 2. מדמים מצב שבו אין דאטה-בייס
    app.state.db_pool = None
    
    try:
        # 3. מנסים לגשת לנתיב
        response = client.get("/api/v1/admin/analytics")
        
        # 4. עכשיו אנחנו מצפים לקבל 503 כי עברנו את האבטחה אבל אין DB
        assert response.status_code == 503
        assert response.json()["detail"] == "Database not available"
    finally:
        # 5. מנקים את המעקף כדי לא להרוס בדיקות אחרות
        app.dependency_overrides.clear()