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
    """JWT strategy that includes user role in token claims."""

    async def write_token(self, user) -> str:
        """Generate JWT with user_id and role in claims.

        Args:
            user: User object with id and role attributes

        Returns:
            JWT token string
        """
        data = {
            "sub": str(user.id),
            "role": getattr(user, "role", "user"),
            "aud": self.token_audience,
        }
        return self._encode_jwt(data)

    async def read_token(
        self, token: Optional[str], user_manager=None
    ) -> Optional[str]:
        """Decode JWT and return user_id if valid.

        Args:
            token: JWT token string
            user_manager: Optional user manager (not used here)

        Returns:
            User ID string if token is valid, None otherwise
        """
        if token is None:
            return None

        try:
            payload = self._decode_jwt(token)
            user_id = payload.get("sub")
            return user_id
        except Exception:
            return None

    def _encode_jwt(self, data: dict) -> str:
        """Encode data to JWT using python-jose."""
        from jose import jwt
        import time

        to_encode = data.copy()
        expire = time.time() + (self.lifetime_seconds)
        to_encode["exp"] = expire

        return jwt.encode(to_encode, self.secret, algorithm="HS256")

    def _decode_jwt(self, token: str) -> dict:
        """Decode JWT token."""
        from jose import jwt, JWTError, ExpiredSignatureError

        try:
            # Audience can be a list, so we need to check for any match
            return jwt.decode(
                token,
                self.secret,
                algorithms=["HS256"],
                audience=self.token_audience[0] if self.token_audience else None,
            )
        except ExpiredSignatureError:
            raise
        except JWTError:
            raise


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
