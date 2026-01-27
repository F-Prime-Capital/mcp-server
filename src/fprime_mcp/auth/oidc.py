"""OIDC authentication provider for Microsoft Entra ID."""

import hashlib
import secrets
import base64
import logging
from datetime import datetime, timedelta
from urllib.parse import urlencode

import httpx
from jose import jwt, JWTError
from jose.exceptions import ExpiredSignatureError

from fprime_mcp.config import Settings, get_settings
from fprime_mcp.auth.models import TokenClaims, UserSession, AuthState

logger = logging.getLogger(__name__)


class OIDCProvider:
    """Microsoft Entra ID OIDC authentication provider."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._jwks_cache: dict | None = None
        self._jwks_cache_time: datetime | None = None
        self._oidc_config: dict | None = None

    async def get_oidc_configuration(self) -> dict:
        """Fetch OIDC discovery document."""
        if self._oidc_config:
            return self._oidc_config

        async with httpx.AsyncClient() as client:
            resp = await client.get(self.settings.oidc_discovery_url)
            resp.raise_for_status()
            self._oidc_config = resp.json()
            return self._oidc_config

    async def get_jwks(self, force_refresh: bool = False) -> dict:
        """Fetch JSON Web Key Set for token validation."""
        cache_valid = (
            self._jwks_cache
            and self._jwks_cache_time
            and (datetime.utcnow() - self._jwks_cache_time) < timedelta(hours=24)
        )

        if cache_valid and not force_refresh:
            return self._jwks_cache

        async with httpx.AsyncClient() as client:
            resp = await client.get(self.settings.oidc_jwks_url)
            resp.raise_for_status()
            self._jwks_cache = resp.json()
            self._jwks_cache_time = datetime.utcnow()
            return self._jwks_cache

    def generate_auth_state(self, redirect_uri: str) -> AuthState:
        """Generate OIDC state and nonce for authentication request."""
        # Generate PKCE code verifier and challenge
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip("=")

        return AuthState(
            state=secrets.token_urlsafe(32),
            nonce=secrets.token_urlsafe(32),
            redirect_uri=redirect_uri,
            code_verifier=code_verifier,
        ), code_challenge

    async def build_authorization_url(
        self,
        redirect_uri: str,
        state: str,
        nonce: str,
        code_challenge: str,
        scopes: list[str] | None = None,
    ) -> str:
        """Build the Microsoft Entra ID authorization URL."""
        config = await self.get_oidc_configuration()

        default_scopes = [
            "openid",
            "profile",
            "email",
            f"api://{self.settings.azure_client_id}/access",
        ]
        scopes = scopes or default_scopes

        params = {
            "client_id": self.settings.azure_client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "state": state,
            "nonce": nonce,
            "response_mode": "query",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        return f"{config['authorization_endpoint']}?{urlencode(params)}"

    async def exchange_code_for_tokens(
        self,
        code: str,
        redirect_uri: str,
        code_verifier: str,
    ) -> dict:
        """Exchange authorization code for tokens."""
        config = await self.get_oidc_configuration()

        data = {
            "client_id": self.settings.azure_client_id,
            "client_secret": self.settings.azure_client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": code_verifier,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                config["token_endpoint"],
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if resp.status_code != 200:
                logger.error(f"Token exchange failed: {resp.text}")
                raise ValueError(f"Token exchange failed: {resp.json().get('error_description', 'Unknown error')}")

            return resp.json()

    async def validate_token(self, token: str) -> TokenClaims:
        """Validate and decode a JWT access token."""
        try:
            jwks = await self.get_jwks()

            # Decode header to get key ID
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")

            # Find matching key
            rsa_key = None
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    rsa_key = key
                    break

            if not rsa_key:
                # Try refreshing JWKS
                jwks = await self.get_jwks(force_refresh=True)
                for key in jwks.get("keys", []):
                    if key.get("kid") == kid:
                        rsa_key = key
                        break

            if not rsa_key:
                raise ValueError("Unable to find matching key for token validation")

            # Validate and decode token
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=["RS256"],
                audience=self.settings.azure_client_id,
                issuer=self.settings.oidc_issuer,
                options={
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": True,
                },
            )

            return TokenClaims(**payload)

        except ExpiredSignatureError:
            raise ValueError("Token has expired")
        except JWTError as e:
            logger.error(f"JWT validation error: {e}")
            raise ValueError(f"Invalid token: {e}")

    async def refresh_access_token(self, refresh_token: str) -> dict:
        """Refresh an access token using a refresh token."""
        config = await self.get_oidc_configuration()

        data = {
            "client_id": self.settings.azure_client_id,
            "client_secret": self.settings.azure_client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                config["token_endpoint"],
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if resp.status_code != 200:
                raise ValueError("Failed to refresh token")

            return resp.json()

    def check_fprime_membership(self, claims: TokenClaims) -> bool:
        """Check if the user is a member of the F-Prime group."""
        # Check group membership
        if self.settings.fprime_group_id in claims.groups:
            return True

        # Check app role if configured
        if self.settings.fprime_app_role and self.settings.fprime_app_role in claims.roles:
            return True

        return False

    async def create_user_session(
        self,
        access_token: str,
        refresh_token: str | None,
        expires_in: int,
    ) -> UserSession:
        """Create a user session from tokens."""
        claims = await self.validate_token(access_token)
        is_fprime_member = self.check_fprime_membership(claims)

        return UserSession(
            user_id=claims.user_id,
            display_name=claims.display_name,
            email=claims.email or claims.preferred_username,
            groups=claims.groups,
            roles=claims.roles,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
            is_fprime_member=is_fprime_member,
        )


# Singleton instance
_oidc_provider: OIDCProvider | None = None


def get_oidc_provider() -> OIDCProvider:
    """Get or create OIDC provider instance."""
    global _oidc_provider
    if _oidc_provider is None:
        _oidc_provider = OIDCProvider()
    return _oidc_provider