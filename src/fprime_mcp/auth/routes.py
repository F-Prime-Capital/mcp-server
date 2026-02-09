"""Authentication routes for OIDC login/logout flow."""

import secrets
import logging
from urllib.parse import urlencode
import httpx
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import RedirectResponse, JSONResponse

from fprime_mcp.auth.oidc_config import get_oidc_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])

# In-memory state storage (use Redis in production)
_auth_states: dict[str, dict] = {}


# =============================================================================
# AUTH ROUTES - Do not delete this file!
# =============================================================================


@router.get("/login")
async def login(request: Request):
    """
    Initiate OIDC login flow.
    Redirects to Microsoft Entra ID for authentication.
    """
    config = get_oidc_config()
    
    # Generate state and nonce for CSRF protection
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    
    # Store state for validation on callback
    _auth_states[state] = {"nonce": nonce}
    
    # Build authorization URL
    params = {
        "client_id": config.client_id,
        "response_type": "code",
        "redirect_uri": config.redirect_uri,
        "scope": config.scopes,
        "state": state,
        "nonce": nonce,
        "response_mode": "query",
    }
    
    auth_url = f"{config.authorization_endpoint}?{urlencode(params)}"
    
    return RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)


@router.get("/callback")
async def auth_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
):
    """
    OIDC callback handler.
    Exchanges authorization code for tokens and creates session.
    """
    config = get_oidc_config()
    
    # Handle error response from IdP
    if error:
        logger.error(f"OIDC error: {error} - {error_description}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Authentication failed: {error_description or error}",
        )
    
    # Validate required parameters
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing authorization code or state",
        )
    
    # Validate state (CSRF protection)
    if state not in _auth_states:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired state parameter",
        )
    
    # Remove used state
    stored_state = _auth_states.pop(state)
    
    # Exchange code for tokens
    token_data = {
        "client_id": config.client_id,
        "client_secret": config.client_secret,
        "code": code,
        "redirect_uri": config.redirect_uri,
        "grant_type": "authorization_code",
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            config.token_endpoint,
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        
        if resp.status_code != 200:
            logger.error(f"Token exchange failed: {resp.text}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Failed to exchange authorization code",
            )
        
        tokens = resp.json()
    
    access_token = tokens.get("access_token")
    id_token = tokens.get("id_token")
    
    # Get user info
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            config.userinfo_endpoint,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        
        if resp.status_code == 200:
            user_info = resp.json()
        else:
            user_info = {}
    
    # Create session cookie with token
    response = RedirectResponse(url=config.home_uri, status_code=status.HTTP_302_FOUND)
    
    # Store token in secure cookie
    response.set_cookie(
        key="mcp_session",
        value=access_token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=3600,  # 1 hour
    )
    
    logger.info(f"User {user_info.get('email', 'unknown')} logged in successfully")
    
    return response


@router.get("/user")
async def get_user(request: Request):
    """Get current authenticated user info."""
    config = get_oidc_config()
    
    # Get token from cookie
    token = request.cookies.get("mcp_session")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authenticated",
        )
    
    # Get user info from Microsoft Graph
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            config.userinfo_endpoint,
            headers={"Authorization": f"Bearer {token}"},
        )
        
        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or expired session",
            )
        
        user_info = resp.json()
    
    return JSONResponse(content={
        "email": user_info.get("email"),
        "name": user_info.get("name"),
        "sub": user_info.get("sub"),
    })


@router.get("/logout")
async def logout(request: Request):
    """Log out the current user."""
    config = get_oidc_config()
    
    response = RedirectResponse(url=config.home_uri, status_code=status.HTTP_302_FOUND)
    response.delete_cookie("mcp_session")
    
    return response