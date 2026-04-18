"""Raw SQL analytics queries for admin dashboard.

Phase 6: Admin & Analytics
Requirements: ADMIN-01 (analytics), ADMIN-02 (user/org management)

Uses asyncpg raw SQL (not ORM) for efficient aggregate queries.
All functions accept an asyncpg Connection and return dicts or tuples.
"""
from datetime import datetime, timedelta, timezone
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
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

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
            SELECT user_id, email, role, last_login_at, created_at
            FROM users
            WHERE email ILIKE $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
        """, f"%{email_search}%", page_size, offset)
    else:
        # Get total count without filter
        total = await conn.fetchval("SELECT COUNT(*) FROM users")

        # Get page data without filter
        rows = await conn.fetch("""
            SELECT user_id, email, role, last_login_at, created_at
            FROM users
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2
        """, page_size, offset)

    return [dict(r) for r in rows], total or 0


async def get_model_metrics_kpis(conn: asyncpg.Connection, days: int) -> dict:
    """Fetch aggregated vLLM model performance KPIs for admin dashboard.

    Args:
        conn: asyncpg database connection
        days: Time range in days

    Returns:
        dict with keys:
            - total_analyses: rows in model_metrics in period
            - total_llm_calls: sum of all vLLM calls made
            - total_errors: sum of all vLLM errors
            - error_rate: llm errors / llm calls (0.0 if no calls)
            - fallback_rate: analyses NOT in pure-llm mode / total (0.0 if none)
            - avg_latency_ms: mean of per-request avg latency (None if no LLM calls)
            - min_latency_ms: global minimum latency across all requests
            - max_latency_ms: global maximum latency across all requests
            - mode_llm: count of fully-LLM analyses
            - mode_hybrid: count of hybrid analyses
            - mode_rules_only: count of rules-only analyses
    """
    from datetime import datetime, timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    row = await conn.fetchrow("""
        SELECT
            COUNT(*)                                         AS total_analyses,
            COALESCE(SUM(llm_calls), 0)                      AS total_llm_calls,
            COALESCE(SUM(llm_errors), 0)                     AS total_errors,
            CASE WHEN SUM(llm_calls) > 0
                 THEN ROUND((SUM(llm_errors)::FLOAT / SUM(llm_calls) * 100)::NUMERIC, 1)
                 ELSE 0 END                                  AS error_rate,
            CASE WHEN COUNT(*) > 0
                 THEN ROUND((SUM(CASE WHEN analysis_mode != 'llm' THEN 1 ELSE 0 END)::FLOAT
                             / COUNT(*) * 100)::NUMERIC, 1)
                 ELSE 0 END                                  AS fallback_rate,
            ROUND(AVG(avg_latency_ms)::NUMERIC, 1)           AS avg_latency_ms,
            ROUND(MIN(min_latency_ms)::NUMERIC, 1)           AS min_latency_ms,
            ROUND(MAX(max_latency_ms)::NUMERIC, 1)           AS max_latency_ms,
            SUM(CASE WHEN analysis_mode = 'llm'        THEN 1 ELSE 0 END) AS mode_llm,
            SUM(CASE WHEN analysis_mode = 'hybrid'     THEN 1 ELSE 0 END) AS mode_hybrid,
            SUM(CASE WHEN analysis_mode = 'rules_only' THEN 1 ELSE 0 END) AS mode_rules_only
        FROM model_metrics
        WHERE created_at >= $1
    """, cutoff)

    return {
        "total_analyses":  int(row["total_analyses"] or 0),
        "total_llm_calls": int(row["total_llm_calls"] or 0),
        "total_errors":    int(row["total_errors"] or 0),
        "error_rate":      float(row["error_rate"] or 0.0),
        "fallback_rate":   float(row["fallback_rate"] or 0.0),
        "avg_latency_ms":  float(row["avg_latency_ms"]) if row["avg_latency_ms"] is not None else None,
        "min_latency_ms":  float(row["min_latency_ms"]) if row["min_latency_ms"] is not None else None,
        "max_latency_ms":  float(row["max_latency_ms"]) if row["max_latency_ms"] is not None else None,
        "mode_llm":        int(row["mode_llm"] or 0),
        "mode_hybrid":     int(row["mode_hybrid"] or 0),
        "mode_rules_only": int(row["mode_rules_only"] or 0),
    }


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
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
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
