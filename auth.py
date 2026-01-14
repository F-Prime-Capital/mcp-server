from __future__ import annotations

from dataclasses import dataclass
from config import SETTINGS


class AuthError(Exception):
    pass


@dataclass(frozen=True)
class AuthContext:
    auth_token: str


def require_auth_token(passed_token: str | None) -> AuthContext:
    token = passed_token or SETTINGS.default_auth_token
    if not token:
        raise AuthError(
            "Missing auth token. Pass access_token to tool call or set VC_PROXY_AUTH_TOKEN."
        )
    return AuthContext(auth_token=token)


def authorize_action(_ctx: AuthContext, _action: str) -> None:
    # Fill with MCP-side authorization in addition to API Gateway:
    # - what claims/identity are in the token?
    # - how to map groups/roles to tool permissions?
    # - any row-level security constraints?
    return
