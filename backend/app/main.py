import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.modules.ingestion import router as ingestion_router
from app.modules.analysis import router as analysis_router
from app.modules.admin import router as admin_router
from app.routers.health import router as health_router
from app.db.connection import create_pool
from app.core.redis import init_redis, close_redis
from app.auth.users import (
    auth_router,
    register_router,
    users_router,
    create_db_and_tables,
)
from app.auth.oauth import google_oauth_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - pool creation and cleanup."""
    # Startup: create asyncpg pool
    try:
        app.state.db_pool = await create_pool()
    except Exception as e:
        logger.error(f"Failed to create database pool: {e}")
        app.state.db_pool = None

    # Startup: create SQLAlchemy tables (for FastAPI Users)
    try:
        await create_db_and_tables()
    except Exception as e:
        logger.error(f"Failed to create SQLAlchemy tables: {e}")

    # Startup: initialize Redis for refresh tokens
    try:
        app.state.redis = await init_redis()
        logger.info("Redis connection established")
    except Exception as e:
        logger.warning(f"Redis connection failed (auth will work without refresh): {e}")
        app.state.redis = None

    yield

    # Shutdown: close Redis
    await close_redis()

    # Shutdown: close asyncpg pool
    if app.state.db_pool:
        await app.state.db_pool.close()


app = FastAPI(
    title="Inclusify Backend",
    description="API for checking inclusive language",
    lifespan=lifespan,
)

# CORS configuration
# Default to localhost for development
# Set ALLOWED_ORIGINS env var for production (comma-separated)
_default_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
_env_origins = os.getenv("ALLOWED_ORIGINS", "")
_allowed_origins = (
    [o.strip() for o in _env_origins.split(",") if o.strip()]
    if _env_origins
    else _default_origins
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check router (before API prefix)
app.include_router(health_router)

# Auth routers (FastAPI Users)
app.include_router(auth_router, prefix="/auth/jwt", tags=["Auth"])
app.include_router(register_router, prefix="/auth/jwt", tags=["Auth"])
app.include_router(users_router, prefix="/users", tags=["Users"])

# Google OAuth router
app.include_router(google_oauth_router, prefix="/auth/google", tags=["Auth"])

# API routers
app.include_router(ingestion_router.router, prefix="/api/v1/ingestion", tags=["Ingestion"])
app.include_router(analysis_router.router, prefix="/api/v1/analysis", tags=["Analysis"])
app.include_router(admin_router.router, prefix="/api/v1/admin", tags=["Admin"])


@app.get("/")
async def root():
    return {"message": "Inclusify API is running", "status": "OK"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
