"""
Custom password-reset endpoints with explicit user validation.

Replaces FastAPI Users' built-in /forgot-password + /reset-password router.
The built-in forgot-password silently ignores unknown emails — we return
explicit error codes so the frontend can direct the user to the right action.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from fastapi_users.exceptions import UserNotExists, InvalidResetPasswordToken

from app.auth.users import get_user_manager, UserManager

logger = logging.getLogger(__name__)

router = APIRouter()


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


@router.post("/forgot-password")
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    user_manager: UserManager = Depends(get_user_manager),
):
    """
    Explicit validation before triggering a password reset.

    Error codes returned to the frontend:
    - EMAIL_NOT_FOUND  → email is not registered at all
    - OAUTH_USER       → account uses Google OAuth, has no password
    """
    try:
        user = await user_manager.get_by_email(body.email)
    except UserNotExists:
        raise HTTPException(status_code=404, detail="EMAIL_NOT_FOUND")

    # Google OAuth users have no password — they must sign in with Google
    if user.oauth_accounts:
        raise HTTPException(status_code=400, detail="OAUTH_USER")

    await user_manager.forgot_password(user, request)
    return {"status": "ok"}


@router.post("/reset-password")
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    user_manager: UserManager = Depends(get_user_manager),
):
    """Validate reset token and set a new password."""
    try:
        await user_manager.reset_password(body.token, body.password, request)
    except InvalidResetPasswordToken:
        raise HTTPException(status_code=400, detail="RESET_PASSWORD_BAD_TOKEN")
    return {"status": "ok"}
