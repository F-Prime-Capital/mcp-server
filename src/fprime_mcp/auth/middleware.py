"""Authentication middleware and dependencies for FastAPI."""

import logging
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from fprime_mcp.auth.models import UserSession
from fprime_mcp.auth.session import SessionManager, get_session_manager
from fprime_mcp.auth.oidc import OIDCProvider, get_oidc_provider

logger = logging.getLogger(__name__)

# HTTP Bearer token security scheme
bearer_scheme = HTTPBearer(auto_error=False)


async def get_session_from_cookie(request: Request) -> str | None:
    """Extract session ID from cookie."""
    return request.cookies.get("fprime_session")


async def get_session_from_bearer(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]
) -> str | None:
    """Extract session ID or token from Authorization header."""
    if credentials:
        return credentials.credentials
    return None


async def get_current_session(
    request: Request,
    session_manager: Annotated[SessionManager, Depends(get_session_manager)],
    oidc_provider: Annotated[OIDCProvider, Depends(get_oidc_provider)],
    bearer_token: Annotated[str | None, Depends(get_session_from_bearer)],
) -> UserSession | None:
    """
    Get the current user session from cookie or bearer token.
    Returns None if no valid session found.
    """
    # Try cookie-based session first
    session_id = await get_session_from_cookie(request)
    if session_id:
        session = await session_manager.get_session(session_id)
        if session and not session.is_token_expired:
            return session
        elif session and session.refresh_token:
            # Try to refresh the token
            try:
                tokens = await oidc_provider.refresh_access_token(session.refresh_token)
                new_session = await oidc_provider.create_user_session(
                    tokens["access_token"],
                    tokens.get("refresh_token", session.refresh_token),
                    tokens.get("expires_in", 3600),
                )
                await session_manager.refresh_session(session_id, new_session)
                return new_session
            except Exception as e:
                logger.warning(f"Failed to refresh token: {e}")
                await session_manager.delete_session(session_id)

    # Try bearer token (direct access token)
    if bearer_token:
        try:
            session = await oidc_provider.create_user_session(
                bearer_token,
                None,
                3600,
            )
            return session
        except Exception as e:
            logger.warning(f"Invalid bearer token: {e}")

    return None


async def require_authenticated(
    session: Annotated[UserSession | None, Depends(get_current_session)]
) -> UserSession:
    """Require a valid authenticated session."""
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return session


async def require_fprime_member(
    session: Annotated[UserSession, Depends(require_authenticated)]
) -> UserSession:
    """Require authenticated user to be an F-Prime member."""
    if not session.is_fprime_member:
        logger.warning(f"User {session.user_id} is not an F-Prime member")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="F-Prime membership required. Contact your administrator for access.",
        )
    return session


# Type aliases for dependency injection
AuthenticatedUser = Annotated[UserSession, Depends(require_authenticated)]
FPrimeMember = Annotated[UserSession, Depends(require_fprime_member)]