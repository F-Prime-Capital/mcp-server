"""OIDC Configuration for F-Prime MCP Server."""

import boto3
import json
from dataclasses import dataclass
from functools import lru_cache


@dataclass
class OIDCConfig:
    client_id: str
    client_secret: str
    tenant_id: str
    redirect_uri: str = "http://localhost:8000/auth/callback"
    home_uri: str = "http://localhost:8000/"
    scopes: str = "openid email profile"
    
    @property
    def issuer(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"
    
    @property
    def authorization_endpoint(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/authorize"
    
    @property
    def token_endpoint(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
    
    @property
    def userinfo_endpoint(self) -> str:
        return "https://graph.microsoft.com/oidc/userinfo"
    
    @property
    def jwks_uri(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys"


@lru_cache(maxsize=1)
def get_oidc_config() -> OIDCConfig:
    """Load OIDC configuration from AWS Secrets Manager."""
    secret_name = "webpage_token"
    region_name = "us-east-2"
    
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name=region_name)
    response = client.get_secret_value(SecretId=secret_name)
    secrets = json.loads(response['SecretString'])
    
    return OIDCConfig(
        client_id=secrets['entra_mcp_clientid'],
        client_secret=secrets['entra_mcp_clientsecret'],
        tenant_id='7c2f7d68-9e11-48ca-81bd-362a0baa5fc2'
    )