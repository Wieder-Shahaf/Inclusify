import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.modules.ingestion import router as ingestion_router
from app.modules.analysis import router as analysis_router
from app.routers.health import router as health_router
from app.db.connection import create_pool
from app.core.redis import init_redis, close_redis
from app.auth.users import (
    auth_router,
    register_router,
    users_router,
    create_db_and_tables,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - pool creation and cleanup."""
    # Startup: create asyncpg pool
    app.state.db_pool = await create_pool()

    # Startup: create SQLAlchemy tables (for FastAPI Users)
    await create_db_and_tables()

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
    await app.state.db_pool.close()


app = FastAPI(
    title="Inclusify Backend",
    description="API for checking inclusive language",
    lifespan=lifespan,
)

# CORS middleware - allows frontend to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
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

# API routers
app.include_router(ingestion_router.router, prefix="/api/v1/ingestion", tags=["Ingestion"])
app.include_router(analysis_router.router, prefix="/api/v1/analysis", tags=["Analysis"])


@app.get("/")
async def root():
    return {"message": "Inclusify API is running", "status": "OK"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
