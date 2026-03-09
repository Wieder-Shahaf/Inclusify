"""
JWT authentication backend for FastAPI Users.

Features:
- Custom JWT strategy that includes role in token claims
- Bearer token transport
- Configurable token expiration
"""
from typing import Optional

from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)

from app.core.config import settings


class JWTStrategyWithRole(JWTStrategy):
    """JWT strategy that includes user role in token claims.

    Extends the base JWTStrategy to add the user's role to the JWT claims.
    The read_token method is inherited from the parent class.
    """

    async def write_token(self, user) -> str:
        """Generate JWT with user_id and role in claims.

        Args:
            user: User object with id and role attributes

        Returns:
            JWT token string

        Note: Calls parent's write_token which handles the standard JWT encoding,
        but we need to add role to the claims. We use a custom encode method.
        """
        from jose import jwt
        import time

        data = {
            "sub": str(user.id),
            "role": getattr(user, "role", "user"),
            "aud": self.token_audience,
            "exp": time.time() + self.lifetime_seconds,
        }
        return jwt.encode(data, self.secret, algorithm="HS256")


def get_jwt_strategy() -> JWTStrategyWithRole:
    """Create JWT strategy with configured settings."""
    return JWTStrategyWithRole(
        secret=settings.JWT_SECRET,
        lifetime_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        token_audience=["fastapi-users:auth"],
    )


# Bearer transport for Authorization header
bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")

# Authentication backend combining transport and strategy
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)
