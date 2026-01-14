from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    mcp_name: str = os.getenv("MCP_NAME", "life-sci-vc-mcp")
    environment: str = os.getenv("ENVIRONMENT", "dev")

    # API Gateway base URL that fronts the Lambda proxy.
    # Example pattern (do not assume): https://.../proxy?x=y  (we will append endpoint safely)
    proxy_api_url: str | None = os.getenv("VC_PROXY_API_URL")

    # Optional default token for local testing (in production, pass per-tool-call).
    default_auth_token: str | None = os.getenv("VC_PROXY_AUTH_TOKEN")

    http_timeout_s: float = float(os.getenv("HTTP_TIMEOUT_S", "30"))


SETTINGS = Settings()
