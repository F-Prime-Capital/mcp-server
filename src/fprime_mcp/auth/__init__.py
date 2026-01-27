"""Authentication module for F-Prime MCP Server."""

from fprime_mcp.auth.models import TokenClaims, UserSession, AuthState, LoginResponse
from fprime_mcp.auth.oidc import OIDCProvider, get_oidc_provider
from fprime_mcp.auth.session import SessionManager, get_session_manager
from fprime_mcp.auth.middleware import (
    require_authenticated,
    require_fprime_member,
    AuthenticatedUser,
    FPrimeMember,
)
from fprime_mcp.auth.routes import router as auth_router

__all__ = [
    # Models
    "TokenClaims",
    "UserSession",
    "AuthState",
    "LoginResponse",
    # Providers
    "OIDCProvider",
    "get_oidc_provider",
    # Session
    "SessionManager",
    "get_session_manager",
    # Middleware
    "require_authenticated",
    "require_fprime_member",
    "AuthenticatedUser",
    "FPrimeMember",
    # Routes
    "auth_router",
]