import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.auth.deps import get_current_user_from_token
from app.db import repository as repo
from .schemas import ProfileRead, ProfileUpdate


router = APIRouter()


def _pool(request: Request):
    if not getattr(request.app.state, "db_pool", None):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not available")
    return request.app.state.db_pool


@router.get("/me/history/{run_id}")
async def get_analysis_detail(
    run_id: uuid.UUID,
    request: Request,
    user: dict = Depends(get_current_user_from_token),
):
    pool = _pool(request)
    user_id = uuid.UUID(user["sub"])
    async with pool.acquire() as conn:
        detail = await repo.get_run_details(conn, run_id, user_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return {
        "run_id": str(detail["run_id"]),
        "document_id": str(detail["document_id"]),
        "title": detail["title"],
        "filename": detail["original_filename"],
        "input_type": detail["input_type"],
        "language": detail["detected_language"] or detail["language"],
        "page_count": detail["page_count"],
        "analyzed_at": detail["started_at"].isoformat() if detail["started_at"] else None,
        "runtime_ms": detail["runtime_ms"],
        "status": detail["status"],
        "findings": [
            {
                "finding_id": str(f["finding_id"]),
                "category": f["category"],
                "severity": f["severity"],
                "start_idx": f["start_idx"],
                "end_idx": f["end_idx"],
                "confidence": f["confidence"],
                "explanation": f["explanation"],
                "excerpt": f["excerpt_redacted"],
                "suggestion": f["replacement_text"],
            }
            for f in detail["findings"]
        ],
    }


@router.delete("/me/history/{run_id}", status_code=204)
async def delete_analysis(
    run_id: uuid.UUID,
    request: Request,
    user: dict = Depends(get_current_user_from_token),
):
    pool = _pool(request)
    user_id = uuid.UUID(user["sub"])
    async with pool.acquire() as conn:
        deleted = await repo.soft_delete_run(conn, run_id, user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")


@router.get("/me/profile", response_model=ProfileRead)
async def get_profile(
    request: Request,
    user: dict = Depends(get_current_user_from_token),
):
    pool = _pool(request)
    user_id = uuid.UUID(user["sub"])
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT full_name, profession, institution FROM users WHERE user_id = $1",
            user_id,
        )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return dict(row)


@router.patch("/me/profile", response_model=ProfileRead)
async def update_profile(
    body: ProfileUpdate,
    request: Request,
    user: dict = Depends(get_current_user_from_token),
):
    pool = _pool(request)
    user_id = uuid.UUID(user["sub"])
    updates = body.model_dump(exclude_none=True)
    if not updates:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT full_name, profession, institution FROM users WHERE user_id = $1",
                user_id,
            )
        return dict(row) if row else {}

    set_clauses = ", ".join(f"{k} = ${i + 2}" for i, k in enumerate(updates.keys()))
    values = list(updates.values())
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"UPDATE users SET {set_clauses}, updated_at = NOW() WHERE user_id = $1 "
            f"RETURNING full_name, profession, institution",
            user_id,
            *values,
        )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return dict(row)


@router.get("/me/history")
async def get_history(
    request: Request,
    user: dict = Depends(get_current_user_from_token),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    pool = _pool(request)
    user_id = uuid.UUID(user["sub"])
    async with pool.acquire() as conn:
        analyses = await repo.get_user_history(conn, user_id, limit=limit, offset=offset)
        kpis_raw = await repo.get_user_history_kpis(conn, user_id)

    total = int(kpis_raw["total_analyses"])
    total_findings = int(kpis_raw["total_findings"])

    serialized = []
    for a in analyses:
        serialized.append({
            "run_id": str(a["run_id"]),
            "document_id": str(a["document_id"]),
            "title": a["title"],
            "filename": a["original_filename"],
            "input_type": a["input_type"],
            "language": a["detected_language"] or a["language"],
            "page_count": a["page_count"],
            "analyzed_at": a["started_at"].isoformat() if a["started_at"] else None,
            "runtime_ms": a["runtime_ms"],
            "findings_count": int(a["findings_count"]),
            "findings_low": int(a["findings_low"]),
            "findings_medium": int(a["findings_medium"]),
            "findings_high": int(a["findings_high"]),
        })

    return {
        "kpis": {
            "total_analyses": total,
            "total_findings": total_findings,
            "avg_issues_per_doc": round(total_findings / total, 1) if total > 0 else 0.0,
            "findings_low": int(kpis_raw["findings_low"]),
            "findings_medium": int(kpis_raw["findings_medium"]),
            "findings_high": int(kpis_raw["findings_high"]),
        },
        "analyses": serialized,
        "total": total,
        "limit": limit,
        "offset": offset,
    }
