"""
Application settings loaded from environment variables.

Settings hierarchy:
1. Environment variables (highest priority)
2. .env file
3. Default values
"""
import os
from functools import lru_cache
from typing import Optional
from urllib.parse import quote_plus

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with env var support."""

    # Added extra="ignore" to prevent Pydantic from crashing on unknown variables
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    # JWT Configuration
    JWT_SECRET: str = "dev-secret-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379"

    # vLLM Configuration
    VLLM_URL: str = "http://localhost:8001"
    VLLM_TIMEOUT: float = 120.0
    VLLM_CIRCUIT_FAIL_MAX: int = 3
    VLLM_CIRCUIT_RESET_TIMEOUT: int = 60
    VLLM_MODEL_NAME: str = "inclusify"
    VLLM_MAX_CONCURRENT: int = 16

    # Google OAuth Configuration
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    FRONTEND_URL: str = "http://localhost:3000"

    # Email (Resend)
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "Inclusify <onboarding@resend.dev>"

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