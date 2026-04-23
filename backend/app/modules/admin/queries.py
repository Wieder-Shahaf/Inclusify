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
    email_search: Optional[str] = None,
    institution: Optional[str] = None,
    min_analyses: Optional[int] = None,
) -> tuple[list[dict], int]:
    """Get paginated user list with optional filters.

    Filters: email_search (ILIKE), institution (ILIKE, requires institution column),
    min_analyses (users with >= N analysis_runs via their documents).
    """
    offset = (page - 1) * page_size

    # Build dynamic WHERE conditions and parameter list
    conditions = []
    params: list = []

    if email_search:
        params.append(f"%{email_search}%")
        conditions.append(f"u.email ILIKE ${len(params)}")

    if institution:
        params.append(f"%{institution}%")
        conditions.append(f"u.institution ILIKE ${len(params)}")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    having_clause = ""
    if min_analyses is not None and min_analyses > 0:
        params.append(min_analyses)
        having_clause = f"HAVING COUNT(ar.run_id) >= ${len(params)}"

    base_query = f"""
        SELECT
            u.user_id,
            u.email,
            u.role,
            u.last_login_at,
            u.created_at,
            u.institution,
            COUNT(ar.run_id) AS analysis_count
        FROM users u
        LEFT JOIN documents d ON d.user_id = u.user_id
        LEFT JOIN analysis_runs ar ON ar.document_id = d.document_id
        {where_clause}
        GROUP BY u.user_id, u.email, u.role, u.last_login_at, u.created_at, u.institution
        {having_clause}
    """

    count_query = f"SELECT COUNT(*) FROM ({base_query}) AS sub"
    total = await conn.fetchval(count_query, *params)

    params_with_pagination = params + [page_size, offset]
    limit_idx = len(params_with_pagination) - 1
    offset_idx = len(params_with_pagination)
    rows = await conn.fetch(
        f"{base_query} ORDER BY u.created_at DESC LIMIT ${limit_idx} OFFSET ${offset_idx}",
        *params_with_pagination,
    )

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
    cutoff = datetime.utcnow() - timedelta(days=days)

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


async def get_label_frequency_trends(conn: asyncpg.Connection, days: int) -> list[dict]:
    """Fetch label frequency trends for admin dashboard.

    Groups findings by category over the last `days` window, returning
    count per category and the top-5 most frequent excerpt_redacted values.

    Args:
        conn: asyncpg database connection
        days: Time range in days

    Returns:
        list of dicts: [{category, count, top_phrases: [{phrase, count}, ...]}]
    """
    from datetime import datetime, timedelta
    from collections import Counter

    cutoff = datetime.utcnow() - timedelta(days=days)
    # Hebrew → English category normalization
    _HE_TO_EN: dict[str, str] = {
        'מוטה': 'Biased',
        'שגוי עובדתית': 'Factually Incorrect',
        'סיבתיות כוזבת': 'False Causality',
        'פתולוגיזציה היסטורית': 'Historical Pathologization',
        'ביטול זהות': 'Identity Invalidation',
        'דקדוק שגוי': 'Incorrect Grammar',
        'מידע רפואי שגוי': 'Medical Misinformation',
        'מונח מיושן': 'Outdated Terminology',
        'פוגעני פוטנציאלי': 'Potentially Offensive',
        'סטיגמה חברתית': 'Social Stigma',
        'השתקת שיח': 'Tone Policing',
    }

    rows = await conn.fetch("""
        SELECT f.category,
               COUNT(*) AS total_count,
               ARRAY_AGG(f.excerpt_redacted) AS all_excerpts
        FROM findings f
        JOIN analysis_runs ar ON f.run_id = ar.run_id
        WHERE ar.started_at >= $1
          AND f.excerpt_redacted IS NOT NULL
        GROUP BY f.category
        ORDER BY total_count DESC
    """, cutoff)

    _VALID_CATEGORIES = {
        'Historical Pathologization',
        'Factually Incorrect',
        'Biased',
        'Potentially Offensive',
        'Outdated Terminology',
    }

    # Merge Hebrew and English rows for the same canonical category
    merged: dict[str, dict] = {}
    for row in rows:
        canonical = _HE_TO_EN.get(row['category'], row['category'])
        if canonical not in _VALID_CATEGORIES:
            continue
        if canonical not in merged:
            merged[canonical] = {'count': 0, 'excerpts': []}
        merged[canonical]['count'] += int(row['total_count'])
        merged[canonical]['excerpts'].extend(e for e in row['all_excerpts'] if e)

    result = []
    for category, data in sorted(merged.items(), key=lambda x: -x[1]['count']):
        phrase_counts = Counter(data['excerpts'])
        top5 = [{'phrase': p, 'count': c} for p, c in phrase_counts.most_common(5)]
        result.append({
            'category': category,
            'count': data['count'],
            'top_phrases': top5,
        })
    return result


# ── Rules CRUD ────────────────────────────────────────────────────────────────

async def get_rules_paginated(
    conn: asyncpg.Connection,
    page: int = 1,
    page_size: int = 20,
    language: Optional[str] = None,
    category: Optional[str] = None,
    is_enabled: Optional[bool] = None,
) -> tuple[list[dict], int]:
    """Get paginated list of detection rules with optional filters."""
    offset = (page - 1) * page_size

    conditions: list[str] = []
    params: list = []

    if language:
        params.append(language)
        conditions.append(f"language = ${len(params)}")
    if category:
        params.append(f"%{category}%")
        conditions.append(f"category ILIKE ${len(params)}")
    if is_enabled is not None:
        params.append(is_enabled)
        conditions.append(f"is_enabled = ${len(params)}")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    total = await conn.fetchval(f"SELECT COUNT(*) FROM rules {where}", *params)

    params_paged = params + [page_size, offset]
    rows = await conn.fetch(
        f"""
        SELECT rule_id, language, name, description, category,
               default_severity, pattern_type, pattern_value,
               example_bad, example_good, is_enabled, created_at, updated_at
        FROM rules {where}
        ORDER BY created_at DESC
        LIMIT ${len(params_paged) - 1} OFFSET ${len(params_paged)}
        """,
        *params_paged,
    )
    return [dict(r) for r in rows], total or 0


async def create_rule(conn: asyncpg.Connection, data: dict) -> dict:
    """Insert a new detection rule and return the full row."""
    row = await conn.fetchrow(
        """
        INSERT INTO rules
            (language, name, description, category, default_severity,
             pattern_type, pattern_value, example_bad, example_good)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING rule_id, language, name, description, category,
                  default_severity, pattern_type, pattern_value,
                  example_bad, example_good, is_enabled, created_at, updated_at
        """,
        data['language'],
        data['name'],
        data.get('description'),
        data['category'],
        data.get('default_severity', 'medium'),
        data['pattern_type'],
        data['pattern_value'],
        data.get('example_bad'),
        data.get('example_good'),
    )
    return dict(row)


async def update_rule(conn: asyncpg.Connection, rule_id: str, updates: dict) -> Optional[dict]:
    """Update allowed fields on a rule; returns updated row or None if not found."""
    allowed = {
        'name', 'description', 'category', 'default_severity',
        'pattern_type', 'pattern_value', 'example_bad', 'example_good', 'is_enabled',
    }
    nullable = {'description', 'example_bad', 'example_good'}
    filtered = {k: v for k, v in updates.items() if k in allowed and (v is not None or k in nullable)}
    if not filtered:
        row = await conn.fetchrow("SELECT * FROM rules WHERE rule_id = $1", rule_id)
        return dict(row) if row else None

    set_clauses = [f"{col} = ${i + 2}" for i, col in enumerate(filtered)]
    values = list(filtered.values())

    row = await conn.fetchrow(
        f"""
        UPDATE rules
        SET {', '.join(set_clauses)}
        WHERE rule_id = $1
        RETURNING rule_id, language, name, description, category,
                  default_severity, pattern_type, pattern_value,
                  example_bad, example_good, is_enabled, created_at, updated_at
        """,
        rule_id,
        *values,
    )
    return dict(row) if row else None


async def toggle_rule(conn: asyncpg.Connection, rule_id: str, is_enabled: bool) -> Optional[dict]:
    """Set is_enabled on a rule; returns updated row or None if not found."""
    row = await conn.fetchrow(
        """
        UPDATE rules SET is_enabled = $2
        WHERE rule_id = $1
        RETURNING rule_id, language, name, description, category,
                  default_severity, pattern_type, pattern_value,
                  example_bad, example_good, is_enabled, created_at, updated_at
        """,
        rule_id,
        is_enabled,
    )
    return dict(row) if row else None


async def delete_rule(conn: asyncpg.Connection, rule_id: str) -> bool:
    """Delete a rule by ID. Returns True if a row was deleted."""
    result = await conn.execute("DELETE FROM rules WHERE rule_id = $1", rule_id)
    return result == "DELETE 1"


# ── Feedback ──────────────────────────────────────────────────────────────────

async def get_feedback_paginated(
    conn: asyncpg.Connection,
    page: int = 1,
    page_size: int = 20,
    vote_filter: Optional[str] = None,   # 'up' | 'down' | None
) -> tuple[list[dict], int, int, int]:
    """Return (rows, total_filtered, total_helpful_all, total_false_positive_all)."""
    offset = (page - 1) * page_size

    conditions: list[str] = []
    params: list = []

    if vote_filter in ("up", "down"):
        params.append(vote_filter)
        conditions.append(f"fb.vote = ${len(params)}")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # Count matching rows (respects filter)
    total = await conn.fetchval(
        f"SELECT COUNT(*) FROM feedback fb {where}", *params
    )

    # Overall totals (ignores filter) — for KPI cards
    summary_row = await conn.fetchrow(
        """
        SELECT
            COUNT(*) FILTER (WHERE vote = 'up')   AS total_helpful,
            COUNT(*) FILTER (WHERE vote = 'down')  AS total_false_positive
        FROM feedback
        """
    )
    total_helpful        = int(summary_row["total_helpful"] or 0)
    total_false_positive = int(summary_row["total_false_positive"] or 0)

    params_paged = params + [page_size, offset]
    rows = await conn.fetch(
        f"""
        SELECT
            fb.feedback_id,
            fb.vote,
            fb.feedback_type,
            fb.flagged_text,
            fb.severity,
            fb.start_idx,
            fb.end_idx,
            fb.comment,
            fb.created_at,
            fb.finding_id,
            fb.run_id,
            COALESCE(u.email, 'anonymous') AS user_email
        FROM feedback fb
        LEFT JOIN users u ON fb.user_id = u.user_id
        {where}
        ORDER BY fb.created_at DESC
        LIMIT ${len(params_paged) - 1} OFFSET ${len(params_paged)}
        """,
        *params_paged,
    )
    return [dict(r) for r in rows], total or 0, total_helpful, total_false_positive
