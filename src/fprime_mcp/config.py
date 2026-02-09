"""Configuration management for F-Prime MCP Server."""

import json
import logging
from functools import lru_cache

import boto3
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


def get_aws_secrets() -> dict:
    """Fetch secrets from AWS Secrets Manager."""
    try:
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name='us-east-2'
        )
        response = client.get_secret_value(SecretId='resource_logins')
        secrets = json.loads(response['SecretString'])
        return secrets
    except Exception as e:
        logger.warning(f"Failed to fetch AWS secrets: {e}. Falling back to environment variables.")
        return {}


# Fetch secrets once at module load
_aws_secrets = get_aws_secrets()


class Settings(BaseSettings):
    """Application settings loaded from AWS Secrets Manager and environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Azure Entra ID Configuration
    # These can come from AWS Secrets Manager or environment variables
    azure_tenant_id: str = Field(..., description="Azure AD Tenant ID")
    azure_client_id: str = Field(
        default=_aws_secrets.get('entra_mcp_clientid', ''),
        description="Azure AD Application (Client) ID"
    )
    azure_client_secret: str = Field(
        default=_aws_secrets.get('entra_mcp_secret', ''),
        description="Azure AD Client Secret"
    )

    # F-Prime Authorization
    fprime_group_id: str = Field(..., description="Azure AD Security Group ID for F-Prime members")
    fprime_app_role: str | None = Field(None, description="Optional app role name")

    # Server Configuration
    server_host: str = Field(default="0.0.0.0")
    server_port: int = Field(default=8000)
    server_env: str = Field(default="development")

    # Session Configuration
    session_secret_key: str = Field(..., description="Secret key for session signing")
    session_expire_minutes: int = Field(default=60)

    # Redis Configuration
    redis_url: str | None = Field(default=None)

    # CORS Configuration
    cors_origins: list[str] = Field(default=["http://localhost:3000"])

    # Logging
    log_level: str = Field(default="INFO")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def oidc_authority(self) -> str:
        return f"https://login.microsoftonline.com/{self.azure_tenant_id}"

    @property
    def oidc_discovery_url(self) -> str:
        return f"{self.oidc_authority}/v2.0/.well-known/openid-configuration"

    @property
    def oidc_jwks_url(self) -> str:
        return f"https://login.microsoftonline.com/{self.azure_tenant_id}/discovery/v2.0/keys"

    @property
    def oidc_issuer(self) -> str:
        return f"https://login.microsoftonline.com/{self.azure_tenant_id}/v2.0"

    @property
    def is_production(self) -> bool:
        return self.server_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()