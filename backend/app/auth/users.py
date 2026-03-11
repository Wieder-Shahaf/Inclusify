"""
FastAPI Users configuration and router exports.

Provides:
- Database session management for auth
- User database adapter
- FastAPI Users instance
- Authentication routers
- current_active_user dependency
"""
import uuid
from typing import AsyncGenerator

from fastapi import Depends
from fastapi_users import FastAPIUsers
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.backend import auth_backend
from app.auth.manager import UserManager
from app.auth.schemas import UserCreate, UserRead, UserUpdate
from app.core.config import settings
from app.db.models import Base, User, OAuthAccount

# SQLAlchemy async engine and session factory
engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def create_db_and_tables():
    """Create database tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides async SQLAlchemy session."""
    async with async_session_maker() as session:
        yield session


async def get_user_db(
    session: AsyncSession = Depends(get_async_session),
) -> AsyncGenerator[SQLAlchemyUserDatabase, None]:
    """Dependency that provides user database adapter with OAuth support."""
    yield SQLAlchemyUserDatabase(session, User, OAuthAccount)


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
) -> AsyncGenerator[UserManager, None]:
    """Dependency that provides user manager."""
    yield UserManager(user_db)


# FastAPI Users instance
fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

# Export current_active_user dependency for protecting routes
current_active_user = fastapi_users.current_user(active=True)

# Authentication routers
auth_router = fastapi_users.get_auth_router(auth_backend)
register_router = fastapi_users.get_register_router(UserRead, UserCreate)
users_router = fastapi_users.get_users_router(UserRead, UserUpdate)
