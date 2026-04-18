"""
Redis connection manager for refresh token storage.

Provides:
- Connection pooling for high-concurrency
- Refresh token storage with TTL
- Token validation and invalidation
"""
import redis.asyncio as redis
from typing import Optional

from app.core.config import settings


class RefreshTokenStore:
    """Manages Redis connections and refresh token operations."""

    def __init__(self, url: str, max_connections: int = 50):
        """Initialize Redis manager with connection pool.

        Args:
            url: Redis connection URL (e.g., redis://localhost:6379)
            max_connections: Maximum pool connections
        """
        self.pool = redis.ConnectionPool.from_url(url, max_connections=max_connections)
        self.client = redis.Redis(connection_pool=self.pool)

    async def store_refresh_token(self, user_id: str, token: str, ttl_seconds: int):
        """Store refresh token with expiration.

        Args:
            user_id: User ID (used as key prefix)
            token: Refresh token value
            ttl_seconds: Time-to-live in seconds
        """
        key = f"refresh:{user_id}"
        await self.client.setex(key, ttl_seconds, token)

    async def validate_refresh_token(self, user_id: str, token: str) -> bool:
        """Validate refresh token matches stored value.

        Args:
            user_id: User ID
            token: Token to validate

        Returns:
            True if token matches, False otherwise
        """
        key = f"refresh:{user_id}"
        stored = await self.client.get(key)
        if stored and stored.decode() == token:
            return True
        return False

    async def invalidate_refresh_token(self, user_id: str):
        """Delete refresh token (logout).

        Args:
            user_id: User ID whose token should be invalidated
        """
        key = f"refresh:{user_id}"
        await self.client.delete(key)

    async def close(self):
        """Close Redis connections and pool."""
        await self.client.close()
        await self.pool.disconnect()


# Global Redis manager instance (initialized in lifespan)
redis_manager: Optional["RefreshTokenStore"] = None


async def get_redis() -> RefreshTokenStore:
    """Get Redis manager instance.

    Note: Should only be called after app startup initializes redis_manager.

    Returns:
        RefreshTokenStore instance

    Raises:
        RuntimeError: If called before initialization
    """
    global redis_manager
    if redis_manager is None:
        redis_manager = RefreshTokenStore(settings.REDIS_URL)
    return redis_manager


async def init_redis() -> RefreshTokenStore:
    """Initialize Redis manager (called during app startup).

    Returns:
        Initialized RefreshTokenStore instance
    """
    global redis_manager
    redis_manager = RefreshTokenStore(settings.REDIS_URL)
    return redis_manager


async def close_redis():
    """Close Redis manager (called during app shutdown)."""
    global redis_manager
    if redis_manager is not None:
        await redis_manager.close()
        redis_manager = None
