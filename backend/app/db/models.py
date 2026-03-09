"""
SQLAlchemy models for FastAPI Users integration.

These models work alongside the existing asyncpg-based repository layer.
FastAPI Users requires SQLAlchemy for its built-in user management.
"""
import uuid
from typing import Optional

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTableUUID
from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class User(SQLAlchemyBaseUserTableUUID, Base):
    """User model extending FastAPI Users base.

    Maps to the existing 'users' table in db/schema.sql.
    Additional fields beyond FastAPI Users defaults:
    - role: user permission level (user, org_admin, site_admin)
    - org_id: organization reference (nullable during registration)
    """

    __tablename__ = "users"

    # Override id to match existing schema column name
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        name="user_id",  # Maps to existing column name
    )

    # Additional fields from existing schema
    role: Mapped[str] = mapped_column(
        String(20),
        default="user",
        nullable=False,
    )

    org_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.org_id"),
        nullable=True,  # Nullable during registration, set later
    )

    # Override email to match existing schema (not nullable)
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    # Override hashed_password column name to match existing schema
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        name="password_hash",  # Maps to existing column name
        nullable=False,
    )
