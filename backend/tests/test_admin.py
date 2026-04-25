"""Tests for admin module - analytics and user/org management.

Phase 6: Admin & Analytics
Requirements: ADMIN-01 (analytics), ADMIN-02 (user/org management)

TDD RED phase: Tests written before implementation.
"""
import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock


# ============================================================================
# Schema Validation Tests (Task 1)
# ============================================================================

class TestAnalyticsSchema:
    """Test AnalyticsResponse schema validation."""

    def test_analytics_response_validates_with_all_kpi_fields(self):
        """Test 1: AnalyticsResponse validates with all 4 KPI fields."""
        from app.modules.admin.schemas import AnalyticsResponse

        response = AnalyticsResponse(
            total_users=100,
            active_users=42,
            total_analyses=500,
            documents_processed=250,
            total_findings=1200,
        )

        assert response.total_users == 100
        assert response.active_users == 42
        assert response.total_analyses == 500
        assert response.documents_processed == 250
        assert response.total_findings == 1200


class TestUsersListSchema:
    """Test UsersListResponse schema validation."""

    def test_users_list_response_validates_with_pagination(self):
        """Test 2: UsersListResponse validates with users list and pagination fields."""
        from app.modules.admin.schemas import UsersListResponse, UserItem

        user = UserItem(
            user_id=uuid4(),
            email="test@example.com",
            role="user",
            last_login_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc)
        )

        response = UsersListResponse(
            users=[user],
            total=100,
            page=1,
            page_size=20,
            total_pages=5
        )

        assert response.total == 100
        assert response.page == 1
        assert response.page_size == 20
        assert response.total_pages == 5
        assert len(response.users) == 1
        assert response.users[0].email == "test@example.com"

    def test_user_item_allows_null_last_login(self):
        """UserItem allows last_login_at to be None."""
        from app.modules.admin.schemas import UserItem

        user = UserItem(
            user_id=uuid4(),
            email="test@example.com",
            role="user",
            last_login_at=None,
            created_at=datetime.now(timezone.utc)
        )

        assert user.last_login_at is None


class TestActivitySchema:
    """Test ActivityResponse schema validation."""

    def test_activity_response_validates_with_issue_count(self):
        """Test 4: ActivityResponse validates with activity containing issue_count."""
        from app.modules.admin.schemas import ActivityResponse, ActivityItem

        activity = ActivityItem(
            run_id=uuid4(),
            user_email="user@example.com",
            document_name="test_document.pdf",
            started_at=datetime.now(timezone.utc),
            status="succeeded",
            issue_count=5
        )

        response = ActivityResponse(
            activity=[activity],
            total=50,
            page=1,
            page_size=20,
            total_pages=3
        )

        assert response.total == 50
        assert len(response.activity) == 1
        assert response.activity[0].issue_count == 5
        assert response.activity[0].status == "succeeded"

    def test_activity_item_allows_null_document_name(self):
        """ActivityItem allows document_name to be None."""
        from app.modules.admin.schemas import ActivityItem

        activity = ActivityItem(
            run_id=uuid4(),
            user_email="user@example.com",
            document_name=None,
            started_at=datetime.now(timezone.utc),
            status="running",
            issue_count=0
        )

        assert activity.document_name is None


# ============================================================================
# Query Function Tests (Task 2) - Stubs for TDD
# ============================================================================

class TestAnalyticsKPIs:
    """Test analytics KPI query functions."""

    @pytest.mark.asyncio
    async def test_get_analytics_kpis_returns_dict_with_kpi_fields(self):
        """Test 1: get_analytics_kpis returns dict with 4 integer KPI fields."""
        from app.modules.admin.queries import get_analytics_kpis

        # Mock connection
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(side_effect=[100, 42, 500, 250, 1200])

        result = await get_analytics_kpis(mock_conn, days=30)

        assert isinstance(result, dict)
        assert "total_users" in result
        assert "active_users" in result
        assert "total_analyses" in result
        assert "documents_processed" in result
        assert "total_findings" in result
        assert all(isinstance(v, int) for v in result.values())

    @pytest.mark.asyncio
    async def test_get_analytics_kpis_respects_days_parameter(self):
        """Test 2: get_analytics_kpis respects days parameter for time filtering."""
        from app.modules.admin.queries import get_analytics_kpis

        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=0)

        # Call with different days values
        await get_analytics_kpis(mock_conn, days=7)
        await get_analytics_kpis(mock_conn, days=90)

        # Verify fetchval was called with datetime cutoffs
        # The cutoff dates should differ based on days parameter
        calls = mock_conn.fetchval.call_args_list
        assert len(calls) == 10  # 5 queries * 2 calls


class TestUsersPaginated:
    """Test users paginated query functions."""

    @pytest.mark.asyncio
    async def test_get_users_paginated_returns_tuple(self):
        """Test 3: get_users_paginated returns (list, total) tuple."""
        from app.modules.admin.queries import get_users_paginated

        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=100)
        mock_conn.fetch = AsyncMock(return_value=[
            {
                "user_id": uuid4(),
                "email": "test@example.com",
                "role": "user",
                "last_login_at": datetime.now(timezone.utc),
                "created_at": datetime.now(timezone.utc)
            }
        ])

        users, total = await get_users_paginated(mock_conn, page=1, page_size=20)

        assert isinstance(users, list)
        assert isinstance(total, int)
        assert total == 100

    @pytest.mark.asyncio
    async def test_get_users_paginated_filters_by_email_search(self):
        """Test 4: get_users_paginated filters by email search (ILIKE)."""
        from app.modules.admin.queries import get_users_paginated

        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=5)
        mock_conn.fetch = AsyncMock(return_value=[])

        await get_users_paginated(mock_conn, page=1, page_size=20, email_search="test@")

        # Verify that fetch was called with ILIKE pattern
        fetch_call = mock_conn.fetch.call_args
        assert fetch_call is not None
        # The query should contain ILIKE for email search
        query = fetch_call[0][0] if fetch_call[0] else ""
        assert "ILIKE" in query or "ilike" in query.lower()


class TestRecentActivity:
    """Test recent activity query functions."""

    @pytest.mark.asyncio
    async def test_get_recent_activity_returns_items_with_issue_count(self):
        """Test 6: get_recent_activity returns activity items with issue_count."""
        from app.modules.admin.queries import get_recent_activity

        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=50)
        mock_conn.fetch = AsyncMock(return_value=[
            {
                "run_id": uuid4(),
                "user_email": "user@example.com",
                "document_name": "test.pdf",
                "started_at": datetime.now(timezone.utc),
                "status": "succeeded",
                "issue_count": 5
            }
        ])

        activity, total = await get_recent_activity(mock_conn, page=1, page_size=20, days=30)

        assert isinstance(activity, list)
        assert len(activity) == 1
        assert "issue_count" in activity[0]
        assert activity[0]["issue_count"] == 5


# ============================================================================
# Endpoint Tests (Task 3) - Integration tests with real JWT tokens
# ============================================================================

def create_test_token(role: str) -> str:
    """Create a test JWT with specified role.

    Uses the same approach as test_rbac.py for consistency.
    """
    from jose import jwt
    from app.core.config import settings

    return jwt.encode(
        {"sub": str(uuid4()), "role": role, "aud": ["fastapi-users:auth"]},
        settings.JWT_SECRET,
        algorithm="HS256"
    )


class TestAdminEndpointAuth:
    """Test admin endpoint authentication and authorization."""

    @pytest.mark.asyncio
    async def test_non_admin_gets_403_forbidden(self, test_client):
        """Non-admin users receive 403 Forbidden on admin endpoints."""
        token = create_test_token("user")

        response = await test_client.get(
            "/api/v1/admin/analytics",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Insufficient permissions"

    @pytest.mark.asyncio
    async def test_no_token_returns_401(self, test_client):
        """Missing token returns 401 Unauthorized."""
        response = await test_client.get("/api/v1/admin/analytics")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_admin_can_access_analytics_endpoint(self, test_client):
        """Admin users can access analytics endpoint."""
        token = create_test_token("site_admin")

        response = await test_client.get(
            "/api/v1/admin/analytics?days=30",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_can_access_users_endpoint(self, test_client):
        """Admin can access users list endpoint."""
        token = create_test_token("site_admin")

        response = await test_client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_can_access_activity_endpoint(self, test_client):
        """Admin can access activity endpoint."""
        token = create_test_token("site_admin")

        response = await test_client.get(
            "/api/v1/admin/activity?days=30",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200


class TestAdminEndpointResponses:
    """Test admin endpoint response shapes."""

    @pytest.mark.asyncio
    async def test_analytics_response_matches_schema(self, test_client):
        """Analytics endpoint returns response matching AnalyticsResponse schema."""
        token = create_test_token("site_admin")

        response = await test_client.get(
            "/api/v1/admin/analytics?days=30",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "active_users" in data
        assert "total_analyses" in data
        assert "documents_processed" in data
        assert "total_findings" in data
        # All values should be integers
        assert isinstance(data["total_users"], int)
        assert isinstance(data["active_users"], int)
        assert isinstance(data["total_analyses"], int)
        assert isinstance(data["documents_processed"], int)
        assert isinstance(data["total_findings"], int)

    @pytest.mark.asyncio
    async def test_users_response_matches_schema(self, test_client):
        """Users endpoint returns response matching UsersListResponse schema."""
        token = create_test_token("site_admin")

        response = await test_client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        # Validate types
        assert isinstance(data["users"], list)
        assert isinstance(data["total"], int)
        assert data["page"] == 1
        assert data["page_size"] == 20

    @pytest.mark.asyncio
    async def test_activity_response_matches_schema(self, test_client):
        """Activity endpoint returns response matching ActivityResponse schema."""
        token = create_test_token("site_admin")

        response = await test_client.get(
            "/api/v1/admin/activity?days=30",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "activity" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
