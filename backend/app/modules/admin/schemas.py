"""Pydantic response schemas for admin API endpoints.

Phase 6: Admin & Analytics
Requirements: ADMIN-01 (analytics), ADMIN-02 (user/org management)

Defines response models for:
- Analytics KPI metrics
- Paginated user list
- Paginated organization list with user counts
- Recent activity with issue counts
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class AnalyticsResponse(BaseModel):
    """KPI metrics response for admin dashboard.

    Fields:
        total_users: All users (all time)
        active_users: Users with at least 1 analysis_run in period
        total_analyses: Count of analysis_runs in period
        documents_processed: Distinct documents with succeeded runs in period
    """
    total_users: int
    active_users: int
    total_analyses: int
    documents_processed: int


class UserItem(BaseModel):
    """Single user item for users list.

    Fields:
        user_id: User UUID
        email: User email address
        role: User role (user, org_admin, site_admin)
        org_name: Name of user's organization
        last_login_at: Last login timestamp (nullable)
        created_at: Account creation timestamp
    """
    user_id: UUID
    email: str
    role: str
    org_name: str
    last_login_at: Optional[datetime]
    created_at: datetime


class UsersListResponse(BaseModel):
    """Paginated list of users response.

    Fields:
        users: List of user items
        total: Total number of users (for pagination)
        page: Current page number (1-indexed)
        page_size: Items per page
        total_pages: Total number of pages
    """
    users: list[UserItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class OrgItem(BaseModel):
    """Single organization item for orgs list.

    Fields:
        org_id: Organization UUID
        name: Organization name
        slug: URL-friendly slug (nullable)
        user_count: Number of users in this organization
        created_at: Organization creation timestamp
    """
    org_id: UUID
    name: str
    slug: Optional[str]
    user_count: int
    created_at: datetime


class OrgsListResponse(BaseModel):
    """Paginated list of organizations response.

    Fields:
        organizations: List of organization items
        total: Total number of organizations (for pagination)
        page: Current page number (1-indexed)
        page_size: Items per page
        total_pages: Total number of pages
    """
    organizations: list[OrgItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class ActivityItem(BaseModel):
    """Single activity item for recent activity list.

    Fields:
        run_id: Analysis run UUID
        user_email: Email of user who initiated the analysis
        document_name: Original filename (nullable if not available)
        started_at: When the analysis started
        status: Run status (queued, running, succeeded, failed)
        issue_count: Number of findings from this run
    """
    run_id: UUID
    user_email: str
    document_name: Optional[str]
    started_at: datetime
    status: str
    issue_count: int


class ActivityResponse(BaseModel):
    """Paginated recent activity response.

    Fields:
        activity: List of activity items
        total: Total number of activity records (for pagination)
        page: Current page number (1-indexed)
        page_size: Items per page
        total_pages: Total number of pages
    """
    activity: list[ActivityItem]
    total: int
    page: int
    page_size: int
    total_pages: int
