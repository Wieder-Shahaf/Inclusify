import asyncpg
import json
from typing import Optional


async def get_user_by_email(conn: asyncpg.Connection, email: str):
    return await conn.fetchrow(
        "SELECT user_id, role FROM users WHERE email=$1 LIMIT 1;",
        email,
    )


# Added Optional[str] to explicitly handle guest users (NULL)
async def create_document(
    conn: asyncpg.Connection,
    user_id: Optional[str],
    input_type: str,
    language: str,
    private_mode: bool,
    mime_type: str = "text/plain",
    original_filename: Optional[str] = None,
    text_storage_ref: Optional[str] = None,
    text_sha256: Optional[str] = None,
    title: Optional[str] = None,
    author: Optional[str] = None,
    page_count: Optional[int] = None,
    detected_language: Optional[str] = None,
):
    row = await conn.fetchrow(
        """
        INSERT INTO documents
          (user_id, input_type, language, private_mode, original_filename, mime_type, text_storage_ref, text_sha256, title, author, page_count, detected_language)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
        RETURNING document_id;
        """,
        user_id,
        input_type,
        language,
        private_mode,
        original_filename,
        mime_type,
        text_storage_ref,
        text_sha256,
        title,
        author,
        page_count,
        detected_language,
    )
    return row["document_id"]


async def create_run(conn: asyncpg.Connection, document_id, model_version: str, status: str, config_snapshot: dict):
    row = await conn.fetchrow(
        """
        INSERT INTO analysis_runs
          (document_id, status, model_version, config_snapshot, started_at)
        VALUES ($1,$2,$3,$4::jsonb, NOW())
        RETURNING run_id;
        """,
        document_id,
        status,
        model_version,
        json.dumps(config_snapshot, ensure_ascii=False),
    )
    return row["run_id"]


#  Added error_message parameter to handle 'failed' runs
async def finish_run(
    conn: asyncpg.Connection, 
    run_id, 
    status: str, 
    runtime_ms: int, 
    error_message: Optional[str] = None
):
    await conn.execute(
        """
        UPDATE analysis_runs
        SET status=$1, finished_at=NOW(), runtime_ms=$2, error_message=$3
        WHERE run_id=$4;
        """,
        status,
        runtime_ms,
        error_message,
        run_id,
    )


async def insert_finding(
    conn: asyncpg.Connection,
    run_id,
    category: str,
    severity: str,
    start_idx: int,
    end_idx: int,
    explanation: Optional[str] = None,
    excerpt_redacted: Optional[str] = None,
    confidence=None,
):
    row = await conn.fetchrow(
        """
        INSERT INTO findings
          (run_id, category, severity, start_idx, end_idx, confidence, explanation, excerpt_redacted)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
        RETURNING finding_id;
        """,
        run_id,
        category,
        severity,
        start_idx,
        end_idx,
        confidence,
        explanation,
        excerpt_redacted,
    )
    return row["finding_id"]


async def insert_suggestion(
    conn: asyncpg.Connection,
    finding_id,
    language: str,
    replacement_text: str,
    rationale: Optional[str] = None,
    source_id=None,
):
    await conn.execute(
        """
        INSERT INTO suggestions
          (finding_id, language, replacement_text, rationale, source_id)
        VALUES ($1,$2,$3,$4,$5);
        """,
        finding_id,
        language,
        replacement_text,
        rationale,
        source_id,
    )


async def get_user_history(
    conn: asyncpg.Connection,
    user_id,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    rows = await conn.fetch(
        """
        SELECT
            ar.run_id,
            ar.started_at,
            ar.finished_at,
            ar.runtime_ms,
            d.document_id,
            d.original_filename,
            d.title,
            d.input_type,
            d.language,
            d.detected_language,
            d.page_count,
            COUNT(f.finding_id)                                       AS findings_count,
            COUNT(CASE WHEN f.severity = 'low'    THEN 1 END)        AS findings_low,
            COUNT(CASE WHEN f.severity = 'medium' THEN 1 END)        AS findings_medium,
            COUNT(CASE WHEN f.severity = 'high'   THEN 1 END)        AS findings_high
        FROM analysis_runs ar
        JOIN documents d ON ar.document_id = d.document_id
        LEFT JOIN findings f ON f.run_id = ar.run_id
        WHERE d.user_id = $1
          AND ar.status = 'succeeded'
          AND d.deleted_at IS NULL
        GROUP BY ar.run_id, ar.started_at, ar.finished_at, ar.runtime_ms,
                 d.document_id, d.original_filename, d.title, d.input_type,
                 d.language, d.detected_language, d.page_count
        ORDER BY ar.started_at DESC
        LIMIT $2 OFFSET $3
        """,
        user_id,
        limit,
        offset,
    )
    return [dict(r) for r in rows]


async def get_user_history_kpis(
    conn: asyncpg.Connection,
    user_id,
) -> dict:
    row = await conn.fetchrow(
        """
        SELECT
            COUNT(DISTINCT ar.run_id)                                  AS total_analyses,
            COUNT(f.finding_id)                                        AS total_findings,
            COUNT(CASE WHEN f.severity = 'low'    THEN 1 END)         AS findings_low,
            COUNT(CASE WHEN f.severity = 'medium' THEN 1 END)         AS findings_medium,
            COUNT(CASE WHEN f.severity = 'high'   THEN 1 END)         AS findings_high
        FROM analysis_runs ar
        JOIN documents d ON ar.document_id = d.document_id
        LEFT JOIN findings f ON f.run_id = ar.run_id
        WHERE d.user_id = $1
          AND ar.status = 'succeeded'
          AND d.deleted_at IS NULL
        """,
        user_id,
    )
    if row:
        return dict(row)
    return {"total_analyses": 0, "total_findings": 0, "findings_low": 0, "findings_medium": 0, "findings_high": 0}


async def get_run_details(conn: asyncpg.Connection, run_id, user_id) -> Optional[dict]:
    row = await conn.fetchrow(
        """
        SELECT ar.run_id, ar.started_at, ar.finished_at, ar.runtime_ms, ar.status,
               d.document_id, d.original_filename, d.title, d.input_type,
               d.language, d.detected_language, d.page_count
        FROM analysis_runs ar
        JOIN documents d ON ar.document_id = d.document_id
        WHERE ar.run_id = $1 AND d.user_id = $2 AND d.deleted_at IS NULL
        """,
        run_id,
        user_id,
    )
    if not row:
        return None
    findings = await conn.fetch(
        """
        SELECT f.finding_id, f.category, f.severity, f.start_idx, f.end_idx,
               f.confidence, f.explanation, f.excerpt_redacted,
               s.replacement_text
        FROM findings f
        LEFT JOIN suggestions s ON s.finding_id = f.finding_id
        WHERE f.run_id = $1
        ORDER BY f.start_idx
        """,
        run_id,
    )
    result = dict(row)
    result["findings"] = [dict(f) for f in findings]
    return result


async def soft_delete_run(conn: asyncpg.Connection, run_id, user_id) -> bool:
    result = await conn.execute(
        """
        UPDATE documents SET deleted_at = NOW()
        WHERE document_id = (
            SELECT document_id FROM analysis_runs WHERE run_id = $1
        ) AND user_id = $2 AND deleted_at IS NULL
        """,
        run_id,
        user_id,
    )
    return result == "UPDATE 1"


async def insert_feedback(
    conn: asyncpg.Connection,
    feedback_type: str,
    vote: str,
    run_id=None,
    finding_id=None,
    user_id=None,
    flagged_text: Optional[str] = None,
    severity: Optional[str] = None,
    start_idx: Optional[int] = None,
    end_idx: Optional[int] = None,
    comment: Optional[str] = None,
) -> str:
    row = await conn.fetchrow(
        """
        INSERT INTO feedback
          (run_id, finding_id, user_id, feedback_type, vote,
           flagged_text, severity, start_idx, end_idx, comment)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
        RETURNING feedback_id;
        """,
        run_id,
        finding_id,
        user_id,
        feedback_type,
        vote,
        flagged_text,
        severity,
        start_idx,
        end_idx,
        comment,
    )
    return row["feedback_id"]


async def insert_model_metric(conn: asyncpg.Connection, data: dict) -> None:
    """Insert one row of per-request vLLM inference metrics.

    Args:
        conn: asyncpg connection (caller manages transaction if needed).
        data: Dict produced by CallMetrics.to_insert_dict().
    """
    await conn.execute(
        """
        INSERT INTO model_metrics (
            analysis_mode,
            total_sentences,
            llm_calls,
            llm_successes,
            llm_errors,
            llm_timeouts,
            circuit_breaker_trips,
            avg_latency_ms,
            min_latency_ms,
            max_latency_ms,
            total_runtime_ms
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11);
        """,
        data["analysis_mode"],
        data["total_sentences"],
        data["llm_calls"],
        data["llm_successes"],
        data["llm_errors"],
        data["llm_timeouts"],
        data["circuit_breaker_trips"],
        data["avg_latency_ms"],
        data["min_latency_ms"],
        data["max_latency_ms"],
        data["total_runtime_ms"],
    )
