"""Authentication module for F-Prime MCP Server."""

from fprime_mcp.auth.oidc_config import OIDCConfig, get_oidc_config
from fprime_mcp.auth.routes import router as auth_router

__all__ = [
    "OIDCConfig",
    "get_oidc_config", 
    "auth_router",
]