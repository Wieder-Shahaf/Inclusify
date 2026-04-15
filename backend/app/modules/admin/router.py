"""Admin API router with protected endpoints.

Phase 6: Admin & Analytics
Requirements: ADMIN-01 (analytics), ADMIN-02 (user/org management)

All endpoints require site_admin role (403 for non-admins).
"""
from fastapi import APIRouter, Depends, Query, Request, HTTPException, status

from app.auth.deps import require_admin
from .schemas import (
    AnalyticsResponse,
    UsersListResponse,
    ActivityResponse,
    ModelMetricsResponse,
)
from . import queries


router = APIRouter()

def _verify_db_pool(request: Request):
    """Verify that DB pool is initialized, else raise 503."""
    if not getattr(request.app.state, "db_pool", None):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not available"
        )
    return request.app.state.db_pool


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    request: Request,
    user: dict = Depends(require_admin),
    days: int = Query(default=30, ge=1, le=365, description="Time range in days")
):
    """Get KPI metrics for admin dashboard."""
    pool = _verify_db_pool(request)
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
    """Get paginated list of users with optional email search."""
    pool = _verify_db_pool(request)
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


@router.get("/model-metrics", response_model=ModelMetricsResponse)
async def get_model_metrics(
    request: Request,
    user: dict = Depends(require_admin),
    days: int = Query(default=30, ge=1, le=365, description="Time range in days")
):
    """Get vLLM model performance KPIs for admin dashboard."""
    pool = _verify_db_pool(request)
    async with pool.acquire() as conn:
        return await queries.get_model_metrics_kpis(conn, days)


@router.get("/activity", response_model=ActivityResponse)
async def get_recent_activity(
    request: Request,
    user: dict = Depends(require_admin),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    days: int = Query(default=30, ge=1, le=365, description="Time range in days")
):
    """Get recent analysis activity for admin dashboard."""
    pool = _verify_db_pool(request)
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
    