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
    file_storage_ref: Optional[str] = None,
    text_sha256: Optional[str] = None,
    title: Optional[str] = None,
    author: Optional[str] = None,
    page_count: Optional[int] = None,
    detected_language: Optional[str] = None,
):
    row = await conn.fetchrow(
        """
        INSERT INTO documents
          (user_id, input_type, language, private_mode, original_filename, mime_type, text_storage_ref, file_storage_ref, text_sha256, title, author, page_count, detected_language)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
        RETURNING document_id;
        """,
        user_id,
        input_type,
        language,
        private_mode,
        original_filename,
        mime_type,
        text_storage_ref,
        file_storage_ref,
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
    rule_id=None,
    confidence=None,
):
    row = await conn.fetchrow(
        """
        INSERT INTO findings
          (run_id, category, severity, start_idx, end_idx, confidence, explanation, rule_id, excerpt_redacted)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
        RETURNING finding_id;
        """,
        run_id,
        category,
        severity,
        start_idx,
        end_idx,
        confidence,
        explanation,
        rule_id,
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
