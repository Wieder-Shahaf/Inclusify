"""Admin API router with protected endpoints.

Phase 6: Admin & Analytics
Requirements: ADMIN-01 (analytics), ADMIN-02 (user/org management)

All endpoints require site_admin role (403 for non-admins).
"""
from fastapi import APIRouter, Depends, Query, Request

from app.auth.deps import require_admin
from .schemas import (
    AnalyticsResponse,
    UsersListResponse,
    ActivityResponse
)
from . import queries


router = APIRouter()


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    request: Request,
    user: dict = Depends(require_admin),
    days: int = Query(default=30, ge=1, le=365, description="Time range in days")
):
    """Get KPI metrics for admin dashboard.

    Returns analytics for the specified time period:
    - total_users: All users (all time)
    - active_users: Users with at least 1 analysis in period
    - total_analyses: Number of analysis runs in period
    - documents_processed: Distinct documents with succeeded runs in period

    Time range options: 7, 30, 90, 365 days (per CONTEXT.md).
    Default: 30 days.

    Requires: site_admin role
    """
    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        return await queries.get_analytics_kpis(conn, days)


@router.get("/users", response_model=UsersListResponse)
async def list_users(
    request: Request,
    user: dict = Depends(require_admin),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    search: str = Query(default=None, max_length=100, description="Email search filter")
):
    """Get paginated list of users with optional email search.

    Returns users with: email, role, org_name, last_login_at, created_at.
    View-only endpoint (no create/edit in v1).

    Requires: site_admin role
    """
    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        users, total = await queries.get_users_paginated(conn, page, page_size, search)
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return {
            "users": users,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }


@router.get("/activity", response_model=ActivityResponse)
async def get_recent_activity(
    request: Request,
    user: dict = Depends(require_admin),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    days: int = Query(default=30, ge=1, le=365, description="Time range in days")
):
    """Get recent analysis activity for admin dashboard.

    Returns activity with: user_email, document_name, started_at, status, issue_count.
    Paginated with 20 items per page (per CONTEXT.md).

    Requires: site_admin role
    """
    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        activity, total = await queries.get_recent_activity(conn, page, page_size, days)
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return {
            "activity": activity,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }
