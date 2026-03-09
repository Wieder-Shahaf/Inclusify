from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.modules.ingestion import router as ingestion_router
from app.modules.analysis import router as analysis_router
from app.routers.health import router as health_router
from app.db.connection import create_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - pool creation and cleanup."""
    # Startup: create pool
    app.state.db_pool = await create_pool()
    yield
    # Shutdown: close pool
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

# API routers
app.include_router(ingestion_router.router, prefix="/api/v1/ingestion", tags=["Ingestion"])
app.include_router(analysis_router.router, prefix="/api/v1/analysis", tags=["Analysis"])


@app.get("/")
async def root():
    return {"message": "Inclusify API is running", "status": "OK"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
