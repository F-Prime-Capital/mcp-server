"""Authentication data models."""

from datetime import datetime
from pydantic import BaseModel, Field


class TokenClaims(BaseModel):
    """Validated JWT token claims."""

    sub: str = Field(..., description="Subject (user ID)")
    oid: str | None = Field(None, description="Object ID in Azure AD")
    preferred_username: str | None = Field(None, description="User's email/UPN")
    name: str | None = Field(None, description="User's display name")
    email: str | None = Field(None, description="User's email address")
    groups: list[str] = Field(default_factory=list, description="Group memberships")
    roles: list[str] = Field(default_factory=list, description="App roles")
    aud: str = Field(..., description="Audience (client ID)")
    iss: str = Field(..., description="Issuer")
    exp: int = Field(..., description="Expiration timestamp")
    iat: int = Field(..., description="Issued at timestamp")
    nbf: int | None = Field(None, description="Not before timestamp")

    @property
    def is_expired(self) -> bool:
        return datetime.utcnow().timestamp() > self.exp

    @property
    def user_id(self) -> str:
        return self.oid or self.sub

    @property
    def display_name(self) -> str:
        return self.name or self.preferred_username or self.sub


class UserSession(BaseModel):
    """User session data stored server-side."""

    user_id: str
    display_name: str
    email: str | None
    groups: list[str]
    roles: list[str]
    access_token: str
    refresh_token: str | None = None
    token_expires_at: datetime
    session_created_at: datetime = Field(default_factory=datetime.utcnow)
    is_fprime_member: bool = False

    @property
    def is_token_expired(self) -> bool:
        return datetime.utcnow() > self.token_expires_at


class AuthState(BaseModel):
    """OIDC authentication state for CSRF protection."""

    state: str
    nonce: str
    redirect_uri: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    code_verifier: str | None = None  # For PKCE


class LoginResponse(BaseModel):
    """Response after successful login."""

    message: str = "Login successful"
    user: str
    session_id: str
    expires_at: datetime


class AuthErrorResponse(BaseModel):
    """Authentication error response."""

    error: str
    error_description: str | None = None
    redirect_to_login: bool = True