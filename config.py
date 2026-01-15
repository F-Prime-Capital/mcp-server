from __future__ import annotations

import os
from dataclasses import dataclass


def _as_bool(v: str | None, default: bool = False) -> bool:
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "t", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    # -----------------
    # MCP server
    # -----------------
    mcp_name: str = os.getenv("MCP_NAME", "life-sci-vc-mcp")
    environment: str = os.getenv("ENVIRONMENT", "dev")

    # API Gateway base URL that fronts a Lambda proxy.
    # Example pattern: https://.../proxy?x=y (we will append endpoint safely)
    proxy_api_url: str | None = os.getenv("VC_PROXY_API_URL")

    # Optional default token for local testing (in production, pass per-tool-call).
    default_auth_token: str | None = os.getenv("VC_PROXY_AUTH_TOKEN")

    http_timeout_s: float = float(os.getenv("HTTP_TIMEOUT_S", "30"))

    # -----------------
    # Optional AWS Secrets Manager fallback (mirrors reference Lambda)
    # -----------------
    use_secrets_manager: bool = _as_bool(os.getenv("USE_SECRETS_MANAGER"), False)
    resource_logins_secret_name: str = os.getenv("RESOURCE_LOGINS_SECRET_NAME", "resource_logins")
    aws_region: str = os.getenv("AWS_REGION", "us-east-2")

    # -----------------
    # Therapeutics Landscape (Box + websites Airtable + GlobalData)
    # -----------------
    airtable_api_key: str | None = os.getenv("AIRTABLE_API_KEY")
    globaldata_token: str | None = os.getenv("GLOBALDATA_TOKEN")

    globaldata_endpoint: str = os.getenv(
        "GLOBALDATA_ENDPOINT",
        "https://apidata.globaldata.com/GlobalDataPharmaFPrimeCapital/api/Drugs/GetPipelineDrugDetails",
    )

    # Airtable identifiers (defaults match the reference code)
    tl_box_base_id: str = os.getenv("TL_BOX_BASE_ID", "app5UNM2QAx82W51F")
    tl_box_table_id: str = os.getenv("TL_BOX_TABLE_ID", "tblI1yQG9E29bCxf0")
    tl_website_base_id: str = os.getenv("TL_WEBSITE_BASE_ID", "apphoxAZN32kVwxUg")
    tl_website_table_id: str = os.getenv("TL_WEBSITE_TABLE_ID", "tblPaRzrVeKmaLh1A")

    # Cache settings
    tl_cache_ttl_s: int = int(os.getenv("TL_CACHE_TTL_S", "600"))
    tl_cache_maxsize: int = int(os.getenv("TL_CACHE_MAXSIZE", "8"))
    tl_cache_dir: str = os.getenv("TL_CACHE_DIR", "/tmp")


SETTINGS = Settings()
