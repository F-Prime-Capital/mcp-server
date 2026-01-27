"""Authentication routes for OIDC login/logout flow."""

import logging
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse

from fprime_mcp.config import Settings, get_settings
from fprime_mcp.auth.oidc import OIDCProvider, get_oidc_provider
from fprime_mcp.auth.session import SessionManager, get_session_manager
from fprime_mcp.auth.models import LoginResponse, AuthErrorResponse
from fprime_mcp.auth.middleware import AuthenticatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/login")
async def login(
    request: Request,
    oidc_provider: Annotated[OIDCProvider, Depends(get_oidc_provider)],
    session_manager: Annotated[SessionManager, Depends(get_session_manager)],
    settings: Annotated[Settings, Depends(get_settings)],
    redirect_uri: str | None = None,
):
    """
    Initiate OIDC login flow.
    Redirects to Microsoft Entra ID for authentication.
    """
    # Build callback URL
    callback_url = str(request.url_for("auth_callback"))

    # Generate auth state for CSRF protection and PKCE
    auth_state, code_challenge = oidc_provider.generate_auth_state(
        redirect_uri=redirect_uri or "/"
    )

    # Save auth state
    await session_manager.save_auth_state(auth_state)

    # Build authorization URL
    auth_url = await oidc_provider.build_authorization_url(
        redirect_uri=callback_url,
        state=auth_state.state,
        nonce=auth_state.nonce,
        code_challenge=code_challenge,
    )

    return RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)


@router.get("/callback", name="auth_callback")
async def auth_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
    oidc_provider: OIDCProvider = Depends(get_oidc_provider),
    session_manager: SessionManager = Depends(get_session_manager),
    settings: Settings = Depends(get_settings),
):
    """
    OIDC callback handler.
    Exchanges authorization code for tokens and creates session.
    """
    # Handle error response from IdP
    if error:
        logger.error(f"OIDC error: {error} - {error_description}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Authentication failed: {error_description or error}",
        )

    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing authorization code or state",
        )

    # Validate state (CSRF protection)
    auth_state = await session_manager.validate_auth_state(state)
    if not auth_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state parameter",
        )

    # Exchange code for tokens
    callback_url = str(request.url_for("auth_callback"))
    try:
        tokens = await oidc_provider.exchange_code_for_tokens(
            code=code,
            redirect_uri=callback_url,
            code_verifier=auth_state.code_verifier,
        )
    except ValueError as e:
        logger.error(f"Token exchange failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Create user session
    try:
        user_session = await oidc_provider.create_user_session(
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token"),
            expires_in=tokens.get("expires_in", 3600),
        )
    except ValueError as e:
        logger.error(f"Session creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    # Check F-Prime membership
    if not user_session.is_fprime_member:
        logger.warning(f"User {user_session.user_id} is not an F-Prime member")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You must be an F-Prime member to use this service.",
        )

    # Save session
    session_id = await session_manager.create_session(user_session)

    # Build response with session cookie
    redirect_to = auth_state.redirect_uri or "/"
    response = RedirectResponse(url=redirect_to, status_code=status.HTTP_302_FOUND)

    # Set secure cookie
    response.set_cookie(
        key="fprime_session",
        value=session_id,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.session_expire_minutes * 60,
    )

    logger.info(f"User {user_session.display_name} logged in successfully")
    return response


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    session_manager: Annotated[SessionManager, Depends(get_session_manager)],
):
    """Log out the current user by clearing the session."""
    session_id = request.cookies.get("fprime_session")
    if session_id:
        await session_manager.delete_session(session_id)

    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("fprime_session")
    return response


@router.get("/me")
async def get_current_user(user: AuthenticatedUser):
    """Get information about the currently authenticated user."""
    return {
        "user_id": user.user_id,
        "display_name": user.display_name,
        "email": user.email,
        "is_fprime_member": user.is_fprime_member,
        "groups": user.groups,
        "roles": user.roles,
        "token_expires_at": user.token_expires_at.isoformat(),
    }


@router.get("/token")
async def get_access_token(user: AuthenticatedUser):
    """
    Get the current access token.
    Useful for CLI tools that need to make authenticated requests.
    """
    return {
        "access_token": user.access_token,
        "expires_at": user.token_expires_at.isoformat(),
        "token_type": "Bearer",
    }