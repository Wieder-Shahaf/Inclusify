"""
SQLAlchemy models for FastAPI Users integration.

These models work alongside the existing asyncpg-based repository layer.
FastAPI Users requires SQLAlchemy for its built-in user management.
"""
import uuid
from typing import List, Optional

from fastapi_users_db_sqlalchemy import (
    SQLAlchemyBaseUserTableUUID,
    SQLAlchemyBaseOAuthAccountTableUUID,
)
from sqlalchemy import String, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class OAuthAccount(SQLAlchemyBaseOAuthAccountTableUUID, Base):
    """OAuth account link storage.

    Links a user to their OAuth provider accounts (e.g., Google).
    Per user decision: we don't store Google's access/refresh tokens -
    only use Google for identity verification.
    """

    __tablename__ = "oauth_accounts"


class User(SQLAlchemyBaseUserTableUUID, Base):
    """User model extending FastAPI Users base.

    Maps to the existing 'users' table in db/schema.sql.
    Additional fields beyond FastAPI Users defaults:
    - role: user permission level (user, org_admin, site_admin)
    - org_id: organization reference (nullable during registration)

    Note: Uses SQLAlchemy's Uuid type which works with both PostgreSQL and SQLite.
    In PostgreSQL it uses native UUID, in SQLite it uses CHAR(32).
    """

    __tablename__ = "users"

    # Additional fields from existing schema
    role: Mapped[str] = mapped_column(
        String(20),
        default="user",
        nullable=False,
    )

    # org_id references organizations table (FK enforced at PostgreSQL level, not SQLAlchemy)
    # This allows SQLAlchemy to manage auth without needing the full schema
    org_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,  # Nullable during registration, set later
    )

    # OAuth accounts relationship - lazy="joined" for eager loading
    oauth_accounts: Mapped[List["OAuthAccount"]] = relationship(
        "OAuthAccount", lazy="joined"
    )
