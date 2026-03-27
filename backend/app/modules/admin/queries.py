"""Raw SQL analytics queries for admin dashboard.

Phase 6: Admin & Analytics
Requirements: ADMIN-01 (analytics), ADMIN-02 (user/org management)

Uses asyncpg raw SQL (not ORM) for efficient aggregate queries.
All functions accept an asyncpg Connection and return dicts or tuples.
"""
from datetime import datetime, timedelta
from typing import Optional
import asyncpg


async def get_analytics_kpis(conn: asyncpg.Connection, days: int) -> dict:
    """Fetch KPI metrics for admin dashboard.

    Args:
        conn: asyncpg database connection
        days: Time range in days for period-based metrics

    Returns:
        dict with keys:
            - total_users: All users (all time)
            - active_users: Users with at least 1 analysis_run in period
            - total_analyses: Count of analysis_runs in period
            - documents_processed: Distinct documents with succeeded runs in period
    """
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Total users (all time)
    total_users = await conn.fetchval("SELECT COUNT(*) FROM users")

    # Active users (users with at least 1 analysis_run in period)
    # Join through documents to get user_id from analysis_runs
    active_users = await conn.fetchval("""
        SELECT COUNT(DISTINCT d.user_id)
        FROM analysis_runs ar
        JOIN documents d ON ar.document_id = d.document_id
        WHERE ar.started_at >= $1 AND d.user_id IS NOT NULL
    """, cutoff)

    # Total analyses in period
    total_analyses = await conn.fetchval("""
        SELECT COUNT(*) FROM analysis_runs WHERE started_at >= $1
    """, cutoff)

    # Documents processed in period (distinct documents with succeeded runs)
    docs_processed = await conn.fetchval("""
        SELECT COUNT(DISTINCT document_id) FROM analysis_runs
        WHERE started_at >= $1 AND status = 'succeeded'
    """, cutoff)

    return {
        "total_users": total_users or 0,
        "active_users": active_users or 0,
        "total_analyses": total_analyses or 0,
        "documents_processed": docs_processed or 0
    }


async def get_users_paginated(
    conn: asyncpg.Connection,
    page: int = 1,
    page_size: int = 20,
    email_search: Optional[str] = None
) -> tuple[list[dict], int]:
    """Get paginated user list with optional email search.

    Args:
        conn: asyncpg database connection
        page: Page number (1-indexed)
        page_size: Number of items per page
        email_search: Optional email substring to filter by (ILIKE)

    Returns:
        Tuple of (list of user dicts, total count)
    """
    offset = (page - 1) * page_size

    # Build WHERE clause for search
    if email_search:
        # Get total count with search filter
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM users WHERE email ILIKE $1",
            f"%{email_search}%"
        )

        # Get page data with search filter
        rows = await conn.fetch("""
            SELECT u.user_id, u.email, u.role, u.last_login_at, u.created_at,
                   COALESCE(o.name, 'Unassigned') as org_name
            FROM users u
            LEFT JOIN organizations o ON u.org_id = o.org_id
            WHERE u.email ILIKE $1
            ORDER BY u.created_at DESC
            LIMIT $2 OFFSET $3
        """, f"%{email_search}%", page_size, offset)
    else:
        # Get total count without filter
        total = await conn.fetchval("SELECT COUNT(*) FROM users")

        # Get page data without filter
        rows = await conn.fetch("""
            SELECT u.user_id, u.email, u.role, u.last_login_at, u.created_at,
                   COALESCE(o.name, 'Unassigned') as org_name
            FROM users u
            LEFT JOIN organizations o ON u.org_id = o.org_id
            ORDER BY u.created_at DESC
            LIMIT $1 OFFSET $2
        """, page_size, offset)

    return [dict(r) for r in rows], total or 0


async def get_orgs_paginated(
    conn: asyncpg.Connection,
    page: int = 1,
    page_size: int = 20
) -> tuple[list[dict], int]:
    """Get paginated organization list with user counts.

    Args:
        conn: asyncpg database connection
        page: Page number (1-indexed)
        page_size: Number of items per page

    Returns:
        Tuple of (list of org dicts with user_count, total count)
    """
    offset = (page - 1) * page_size

    # Get total count
    total = await conn.fetchval("SELECT COUNT(*) FROM organizations")

    # Get page data with user counts via subquery
    rows = await conn.fetch("""
        SELECT
            o.org_id,
            o.name,
            o.slug,
            o.created_at,
            (SELECT COUNT(*) FROM users u WHERE u.org_id = o.org_id) as user_count
        FROM organizations o
        ORDER BY o.created_at DESC
        LIMIT $1 OFFSET $2
    """, page_size, offset)

    return [dict(r) for r in rows], total or 0


async def get_recent_activity(
    conn: asyncpg.Connection,
    page: int,
    page_size: int,
    days: int
) -> tuple[list[dict], int]:
    """Get recent analysis activity with issue counts.

    Args:
        conn: asyncpg database connection
        page: Page number (1-indexed)
        page_size: Number of items per page
        days: Time range in days

    Returns:
        Tuple of (list of activity dicts with issue_count, total count)
    """
    cutoff = datetime.utcnow() - timedelta(days=days)
    offset = (page - 1) * page_size

    # Count total in period
    total = await conn.fetchval("""
        SELECT COUNT(*) FROM analysis_runs
        WHERE started_at >= $1
    """, cutoff)

    # Get activity with joined data and issue counts
    rows = await conn.fetch("""
        SELECT
            ar.run_id,
            COALESCE(u.email, 'anonymous') as user_email,
            d.original_filename as document_name,
            ar.started_at,
            ar.status,
            (SELECT COUNT(*) FROM findings f WHERE f.run_id = ar.run_id) as issue_count
        FROM analysis_runs ar
        JOIN documents d ON ar.document_id = d.document_id
        LEFT JOIN users u ON d.user_id = u.user_id
        WHERE ar.started_at >= $1
        ORDER BY ar.started_at DESC
        LIMIT $2 OFFSET $3
    """, cutoff, page_size, offset)

    return [dict(r) for r in rows], total or 0
