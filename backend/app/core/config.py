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

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with env var support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
    )

    # JWT Configuration
    JWT_SECRET: str = "dev-secret-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379"

    # vLLM Configuration
    VLLM_URL: str = "http://localhost:8001"
    VLLM_TIMEOUT: float = 30.0
    VLLM_CIRCUIT_FAIL_MAX: int = 3
    VLLM_CIRCUIT_RESET_TIMEOUT: int = 60

    # Database Configuration (SQLAlchemy URL)
    # Constructed from PG* env vars for PostgreSQL, or SQLite for dev
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
                pg_ssl = os.environ.get("PGSSL")

                ssl_suffix = "?sslmode=require" if pg_ssl else ""
                self.DATABASE_URL = (
                    f"postgresql+asyncpg://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}{ssl_suffix}"
                )
            else:
                # Default to SQLite for local development
                self.DATABASE_URL = "sqlite+aiosqlite:///./inclusify.db"
        return self


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()


# Convenience export
settings = get_settings()
