"""
SQLAlchemy models aligned with canonical db/schema.sql.

The User model maps FastAPI Users' expected attributes (id, hashed_password)
to the actual DB column names (user_id, password_hash) using mapped_column.
This lets FastAPI Users work without changing the canonical schema.
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseOAuthAccountTableUUID
from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from fastapi_users_db_sqlalchemy.generics import GUID


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class OAuthAccount(SQLAlchemyBaseOAuthAccountTableUUID, Base):
    """OAuth account link storage.

    Links a user to their OAuth provider accounts (e.g., Google).
    FK references users.user_id (the actual DB column name).
    """

    __tablename__ = "oauth_accounts"

    # Override user_id FK to point to actual column name in users table
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.user_id", ondelete="cascade"), nullable=False
    )


class User(Base):
    """User model for FastAPI Users, mapped to canonical db/schema.sql columns.

    Key mappings (SQLAlchemy attribute → DB column):
    - id → user_id (FastAPI Users expects 'id' as PK attribute)
    - hashed_password → password_hash (FastAPI Users expects 'hashed_password')

    This avoids changing the canonical schema while satisfying FastAPI Users.
    Raw asyncpg queries in admin/queries.py use the actual DB column names.
    """

    __tablename__ = "users"

    # FastAPI Users required fields — mapped to schema.sql column names
    id: Mapped[uuid.UUID] = mapped_column(
        "user_id", GUID, primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(320), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(
        "password_hash", String(1024), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Custom fields from schema.sql
    role: Mapped[str] = mapped_column(
        String(20), default="user", nullable=False
    )
    full_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    profession: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    institution: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # OAuth accounts relationship
    oauth_accounts: Mapped[List["OAuthAccount"]] = relationship(
        "OAuthAccount", lazy="joined"
    )
