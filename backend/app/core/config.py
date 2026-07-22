"""
Application settings loaded from environment variables.

Settings hierarchy:
1. Environment variables (highest priority)
2. .env file
3. Default values
"""
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env regardless of where uvicorn is invoked from.
# Priority: backend/.env → project-root/.env → no file (env vars only)
_THIS_DIR = Path(__file__).resolve().parent          # backend/app/core/
_BACKEND_DIR = _THIS_DIR.parent.parent               # backend/
_ROOT_ENV = _BACKEND_DIR.parent / ".env"             # Inclusify/.env
_LOCAL_ENV = _BACKEND_DIR / ".env"                   # backend/.env  (optional override)
_ENV_FILES = [str(p) for p in (_LOCAL_ENV, _ROOT_ENV) if p.exists()]


class Settings(BaseSettings):
    """Application settings with env var support."""

    # Added extra="ignore" to prevent Pydantic from crashing on unknown variables
    model_config = SettingsConfigDict(
        env_file=_ENV_FILES or None,
        case_sensitive=True,
        extra="ignore",
    )

    # JWT Configuration
    JWT_SECRET: str = "dev-secret-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  # 30 days — matches localStorage expiry in OAuth callback
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379"

    # vLLM Configuration
    VLLM_URL: str = "http://localhost:8001"
    # Bearer token for the vLLM server (--api-key). Empty = no Authorization
    # header (e.g. local dev against an unauthenticated server).
    VLLM_API_KEY: str = ""
    # Modal cold start (torch.compile + CUDA-graph capture, cache lost on
    # scale-to-zero) runs ~2-3 min, so the first request after idle needs a wide
    # timeout and extra breaker headroom to avoid tripping on a healthy warmup.
    VLLM_TIMEOUT: float = 240.0
    VLLM_CIRCUIT_FAIL_MAX: int = 5
    VLLM_CIRCUIT_RESET_TIMEOUT: int = 60
    VLLM_MODEL_NAME: str = "inclusify"
    # Max concurrent GPU calls across ALL users. Must match --max-num-seqs in vllm.service.
    # Current VM: T4 + Qwen2.5-3B, max-num-seqs=16. Raise when adding GPU capacity.
    VLLM_MAX_CONCURRENT: int = 16
    # When True, vLLM errors return a simulated response instead of None (for load testing only).
    VLLM_LOAD_TEST_MODE: bool = False

    # Model health-check behaviour (see /api/v1/health/model and
    # docs/STACK-A-MIGRATION.md §2.3). When the GPU layer is serverless and
    # scales to zero (Modal), set MODEL_SCALE_TO_ZERO=True: the health endpoint
    # must NOT probe vLLM, because any request wakes the GPU and bills idle time.
    # In that mode availability is inferred from the circuit breaker (real
    # analysis traffic) and the model is reported available so Modal cold-starts
    # only on the first real request. On an always-on backend (Azure VM) keep the
    # live probe but cache it for MODEL_HEALTH_CACHE_TTL seconds so many open
    # analyze tabs can't turn a 30s poll into sustained load on vLLM.
    MODEL_SCALE_TO_ZERO: bool = False
    MODEL_HEALTH_CACHE_TTL: float = 300.0  # seconds; live-probe path only

    # Object storage (S3-compatible: Cloudflare R2 in prod, MinIO in dev).
    # Replaces the Azure Blob settings (docs/STACK-A-MIGRATION.md §2.1). Empty
    # credentials => storage disabled: uploads become no-ops returning None.
    S3_ENDPOINT_URL: str = ""       # R2: https://<ACCT_ID>.r2.cloudflarestorage.com · MinIO: http://minio:9000
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET: str = "texts"        # was AZURE_STORAGE_CONTAINER
    S3_REGION: str = "auto"         # R2 expects "auto"; MinIO ignores it

    # Google OAuth Configuration
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    FRONTEND_URL: str = "http://localhost:3000"

    # Email (Resend). Sender address is read from the RESEND_FROM env var
    # (see contact router / auth manager) — must be a Resend-verified domain.
    RESEND_API_KEY: str = ""

    # Database Configuration
    DATABASE_URL: Optional[str] = None

    @model_validator(mode="after")
    def construct_database_url(self) -> "Settings":
        """Construct DATABASE_URL from PG* env vars if not set."""
        if self.DATABASE_URL is None:
            pg_host = os.environ.get("PGHOST")
            if pg_host:
                pg_port = os.environ.get("PGPORT", "5432")
                pg_db = os.environ.get("PGDATABASE", "inclusify")
                pg_user = os.environ.get("PGUSER", "postgres")
                pg_pass = os.environ.get("PGPASSWORD", "")

                self.DATABASE_URL = (
                    f"postgresql+asyncpg://{quote_plus(pg_user)}:{quote_plus(pg_pass)}@{pg_host}:{pg_port}/{pg_db}"
                )
            else:
                self.DATABASE_URL = "sqlite+aiosqlite:///./inclusify.db"
        return self


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()


settings = get_settings()
