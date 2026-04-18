import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth.deps import get_current_user_from_token
from .schemas import ProfileRead, ProfileUpdate


router = APIRouter()


def _pool(request: Request):
    if not getattr(request.app.state, "db_pool", None):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not available")
    return request.app.state.db_pool


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
