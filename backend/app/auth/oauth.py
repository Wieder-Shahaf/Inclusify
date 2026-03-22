"""
Google OAuth integration for FastAPI Users.

Provides:
- GoogleOAuth2 client configuration
- Custom callback router that redirects to frontend with JWT token
- Account linking by email (per user decision)
"""
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from httpx_oauth.clients.google import GoogleOAuth2
from httpx_oauth.oauth2 import OAuth2Token
from starlette.status import HTTP_302_FOUND

from app.auth.backend import get_jwt_strategy
from app.core.config import settings
from app.db.models import OAuthAccount, User

logger = logging.getLogger(__name__)

# Google OAuth2 client
google_oauth_client = GoogleOAuth2(
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
)

# Router for OAuth endpoints
google_oauth_router = APIRouter()


def get_oauth_callback_url(request: Request) -> str:
    """Build callback URL from current request.

    Behind reverse proxies (Azure Container Apps), the internal request
    arrives as http:// even though the external URL is https://.
    We respect X-Forwarded-Proto if present, otherwise force https in
    production (when host is not localhost).
    """
    url = str(request.url_for("google_callback"))
    forwarded_proto = request.headers.get("x-forwarded-proto")
    if forwarded_proto == "https" and url.startswith("http://"):
        url = "https://" + url[len("http://"):]
    elif "localhost" not in url and url.startswith("http://"):
        url = "https://" + url[len("http://"):]
    return url


@google_oauth_router.get("/authorize")
async def google_authorize(request: Request):
    """Redirect to Google OAuth consent screen.

    The state parameter is handled by httpx-oauth for CSRF protection.
    """
    callback_url = get_oauth_callback_url(request)

    authorization_url = await google_oauth_client.get_authorization_url(
        redirect_uri=callback_url,
        scope=["openid", "email", "profile"],
    )

    return RedirectResponse(url=authorization_url, status_code=HTTP_302_FOUND)


@google_oauth_router.get("/callback", name="google_callback")
async def google_callback(
    request: Request,
    code: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
):
    """Handle Google OAuth callback.

    On success: Exchange code for tokens, create/link user, redirect with JWT.
    On error: Redirect to frontend with error param.
    """
    from app.auth.users import async_session_maker

    frontend_url = settings.FRONTEND_URL.rstrip("/")
    callback_path = "/oauth/callback"

    # Handle OAuth errors from Google
    if error:
        logger.warning(f"OAuth error from Google: {error} - {error_description}")
        return RedirectResponse(
            url=f"{frontend_url}{callback_path}?error={error}",
            status_code=HTTP_302_FOUND,
        )

    if not code:
        logger.warning("OAuth callback missing code parameter")
        return RedirectResponse(
            url=f"{frontend_url}{callback_path}?error=invalid_code",
            status_code=HTTP_302_FOUND,
        )

    try:
        # Exchange code for tokens
        callback_url = get_oauth_callback_url(request)
        token: OAuth2Token = await google_oauth_client.get_access_token(
            code=code,
            redirect_uri=callback_url,
        )

        # Get user info from Google
        async with google_oauth_client.get_httpx_client() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {token['access_token']}"},
            )
            response.raise_for_status()
            google_user = response.json()

        email = google_user.get("email")
        google_id = google_user.get("sub")

        if not email:
            logger.error("Google user info missing email")
            return RedirectResponse(
                url=f"{frontend_url}{callback_path}?error=email_missing",
                status_code=HTTP_302_FOUND,
            )

        # Find or create user
        async with async_session_maker() as session:
            user = await _get_or_create_oauth_user(
                session=session,
                email=email,
                google_id=google_id,
                is_verified=google_user.get("email_verified", False),
            )

            if user is None:
                return RedirectResponse(
                    url=f"{frontend_url}{callback_path}?error=account_disabled",
                    status_code=HTTP_302_FOUND,
                )

        # Generate JWT using same strategy as password login
        jwt_strategy = get_jwt_strategy()
        access_token = await jwt_strategy.write_token(user)

        logger.info(f"OAuth login successful for user {user.id}")

        return RedirectResponse(
            url=f"{frontend_url}{callback_path}?access_token={access_token}",
            status_code=HTTP_302_FOUND,
        )

    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return RedirectResponse(
            url=f"{frontend_url}{callback_path}?error=invalid_code",
            status_code=HTTP_302_FOUND,
        )


async def _get_or_create_oauth_user(
    session,
    email: str,
    google_id: str,
    is_verified: bool,
) -> Optional[User]:
    """Find existing user by email or create new one.

    Per user decisions:
    - Auto-link accounts: If Google email matches existing password account, link automatically
    - Trust Google's email verification
    """
    from sqlalchemy import select

    # First, check if we have an existing OAuth account link
    oauth_account = await session.scalar(
        select(OAuthAccount).where(
            OAuthAccount.oauth_name == "google",
            OAuthAccount.account_id == google_id,
        )
    )

    if oauth_account:
        # Get the linked user
        user = await session.scalar(
            select(User).where(User.id == oauth_account.user_id)
        )
        if user and not user.is_active:
            return None  # Account disabled
        return user

    # Check for existing user with same email (auto-link per user decision)
    user = await session.scalar(select(User).where(User.email == email))

    if user:
        if not user.is_active:
            return None  # Account disabled

        # Link the OAuth account to existing user
        new_oauth_account = OAuthAccount(
            user_id=user.id,
            oauth_name="google",
            account_id=google_id,
            account_email=email,
            access_token="",  # Not storing per user decision
            refresh_token=None,
            expires_at=None,
        )
        session.add(new_oauth_account)

        # Trust Google's email verification
        if is_verified and not user.is_verified:
            user.is_verified = True

        await session.commit()
        logger.info(f"Linked Google account to existing user {user.id}")
        return user

    # Create new user
    new_user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password="",  # OAuth-only user, no password
        is_active=True,
        is_verified=is_verified,  # Trust Google's verification
        is_superuser=False,
        role="user",  # Default role
    )
    session.add(new_user)
    await session.flush()  # Get the user ID

    # Create OAuth account link
    new_oauth_account = OAuthAccount(
        user_id=new_user.id,
        oauth_name="google",
        account_id=google_id,
        account_email=email,
        access_token="",
        refresh_token=None,
        expires_at=None,
    )
    session.add(new_oauth_account)

    await session.commit()
    logger.info(f"Created new OAuth user {new_user.id}")

    return new_user
