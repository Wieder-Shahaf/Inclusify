"""
RBAC (Role-Based Access Control) tests.

Tests the require_role() dependency factory that enforces role-based access control
using JWT claims. Follows the role hierarchy: site_admin > org_admin > user.

Per CONTEXT.md decisions:
- 403 Forbidden with "Insufficient permissions" message for role check failures
- 401 Unauthorized for missing/invalid tokens
- Roles embedded in JWT claims (no DB lookup required)
"""
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from jose import jwt

from app.auth.deps import require_role, ROLE_HIERARCHY
from app.core.config import settings


# Create test app with RBAC-protected endpoints
app = FastAPI()


@app.get("/admin-only", dependencies=[Depends(require_role("site_admin"))])
async def admin_only():
    """Endpoint requiring site_admin role."""
    return {"message": "admin access granted"}


@app.get("/org-admin", dependencies=[Depends(require_role("org_admin"))])
async def org_admin_route():
    """Endpoint requiring org_admin or higher."""
    return {"message": "org admin access granted"}


@app.get("/user-route", dependencies=[Depends(require_role("user"))])
async def user_route():
    """Endpoint requiring any authenticated user."""
    return {"message": "user access granted"}


client = TestClient(app)


def create_token(role: str) -> str:
    """Create a test JWT with specified role."""
    return jwt.encode(
        {"sub": "test-user-id", "role": role, "aud": ["fastapi-users:auth"]},
        settings.JWT_SECRET,
        algorithm="HS256"
    )


class TestRequireRole:
    """Tests for require_role() dependency factory."""

    def test_site_admin_can_access_admin_route(self):
        """site_admin can access site_admin-only route."""
        token = create_token("site_admin")
        response = client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["message"] == "admin access granted"

    def test_org_admin_forbidden_on_admin_route(self):
        """org_admin gets 403 on site_admin-only route."""
        token = create_token("org_admin")
        response = client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403
        assert response.json()["detail"] == "Insufficient permissions"

    def test_user_forbidden_on_admin_route(self):
        """Regular user gets 403 on site_admin-only route."""
        token = create_token("user")
        response = client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403
        assert response.json()["detail"] == "Insufficient permissions"

    def test_site_admin_can_access_org_admin_route(self):
        """site_admin can access org_admin route (higher privilege)."""
        token = create_token("site_admin")
        response = client.get("/org-admin", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200

    def test_org_admin_can_access_org_admin_route(self):
        """org_admin can access org_admin route."""
        token = create_token("org_admin")
        response = client.get("/org-admin", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200

    def test_user_forbidden_on_org_admin_route(self):
        """Regular user gets 403 on org_admin route."""
        token = create_token("user")
        response = client.get("/org-admin", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403

    def test_all_roles_can_access_user_route(self):
        """All authenticated users can access user-level routes."""
        for role in ["user", "org_admin", "site_admin"]:
            token = create_token(role)
            response = client.get("/user-route", headers={"Authorization": f"Bearer {token}"})
            assert response.status_code == 200, f"{role} should access user route"

    def test_no_token_returns_401(self):
        """Missing token returns 401 (not 403)."""
        response = client.get("/user-route")
        assert response.status_code == 401

    def test_invalid_token_returns_401(self):
        """Invalid/expired token returns 401."""
        response = client.get("/user-route", headers={"Authorization": "Bearer invalid.token.here"})
        assert response.status_code == 401


class TestRoleHierarchy:
    """Tests for role hierarchy ordering."""

    def test_hierarchy_order(self):
        """Verify role hierarchy is correctly ordered."""
        assert ROLE_HIERARCHY["site_admin"] > ROLE_HIERARCHY["org_admin"]
        assert ROLE_HIERARCHY["org_admin"] > ROLE_HIERARCHY["user"]
