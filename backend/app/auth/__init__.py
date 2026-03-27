"""
Authentication module for Inclusify.

Provides JWT-based authentication using FastAPI Users.
"""
from app.auth.users import (
    auth_router,
    register_router,
    users_router,
    current_active_user,
    fastapi_users,
    create_db_and_tables,
)
from app.auth.oauth import google_oauth_router
from app.auth.password_reset import router as password_reset_router

__all__ = [
    "auth_router",
    "register_router",
    "users_router",
    "password_reset_router",
    "current_active_user",
    "fastapi_users",
    "create_db_and_tables",
    "google_oauth_router",
]
