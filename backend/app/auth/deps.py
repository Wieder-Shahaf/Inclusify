"""
RBAC (Role-Based Access Control) dependencies for FastAPI.

Provides role-based access control using JWT claims. Roles are embedded in
tokens at login time, enabling fast authorization checks without database lookups.

Role hierarchy: site_admin > org_admin > user

Per CONTEXT.md decisions:
- 403 Forbidden with "Insufficient permissions" (not 404)
- Roles stored in JWT claims
- Higher roles inherit lower role permissions
"""
from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

from app.core.config import settings


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/jwt/login")


# Role hierarchy: higher number = more privileges
ROLE_HIERARCHY = {
    "site_admin": 3,
    "org_admin": 2,
    "user": 1,
}


async def get_current_user_from_token(token: str = Depends(oauth2_scheme)) -> dict:
    """Extract user info from JWT token claims.

    Returns dict with 'sub' (user_id) and 'role' from JWT claims.
    Raises 401 if token is invalid or expired.

    Args:
        token: Bearer token from Authorization header

    Returns:
        JWT payload dict containing 'sub' (user_id), 'role', 'aud', 'exp'

    Raises:
        HTTPException: 401 Unauthorized if token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=["HS256"],
            audience="fastapi-users:auth"
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_role(required_role: str) -> Callable:
    """Dependency factory for role-based access control.

    Creates a FastAPI dependency that validates the current user has at least
    the specified role level. Uses role hierarchy so higher roles can access
    endpoints requiring lower roles.

    Args:
        required_role: Minimum role required ('user', 'org_admin', 'site_admin')

    Returns:
        Dependency that validates user has sufficient role level.
        Returns the user dict (JWT claims) if authorized.
        Raises 403 with "Insufficient permissions" if role check fails.

    Usage:
        @router.get("/admin", dependencies=[Depends(require_role("site_admin"))])
        async def admin_endpoint():
            ...

        @router.get("/data")
        async def get_data(user: dict = Depends(require_role("org_admin"))):
            # user dict available with 'sub' and 'role'
            ...
    """
    async def role_checker(user: dict = Depends(get_current_user_from_token)) -> dict:
        user_role = user.get("role", "user")
        user_level = ROLE_HIERARCHY.get(user_role, 0)
        required_level = ROLE_HIERARCHY.get(required_role, 0)

        if user_level < required_level:
            # Per CONTEXT.md: Return 403 with "Insufficient permissions"
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return user

    return role_checker


# Convenience dependencies for common role checks
require_admin = require_role("site_admin")
require_org_admin = require_role("org_admin")
require_authenticated = require_role("user")
