"""Session management for authenticated users."""

import json
import secrets
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

from fprime_mcp.config import Settings, get_settings
from fprime_mcp.auth.models import UserSession, AuthState

logger = logging.getLogger(__name__)


class SessionStore(ABC):
    """Abstract base class for session storage."""

    @abstractmethod
    async def save_session(self, session_id: str, session: UserSession, ttl_seconds: int) -> None:
        pass

    @abstractmethod
    async def get_session(self, session_id: str) -> UserSession | None:
        pass

    @abstractmethod
    async def delete_session(self, session_id: str) -> None:
        pass

    @abstractmethod
    async def save_auth_state(self, state: str, auth_state: AuthState, ttl_seconds: int) -> None:
        pass

    @abstractmethod
    async def get_auth_state(self, state: str) -> AuthState | None:
        pass

    @abstractmethod
    async def delete_auth_state(self, state: str) -> None:
        pass


class InMemorySessionStore(SessionStore):
    """In-memory session store for development."""

    def __init__(self):
        self._sessions: dict[str, tuple[UserSession, datetime]] = {}
        self._auth_states: dict[str, tuple[AuthState, datetime]] = {}

    async def save_session(self, session_id: str, session: UserSession, ttl_seconds: int) -> None:
        expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        self._sessions[session_id] = (session, expires_at)

    async def get_session(self, session_id: str) -> UserSession | None:
        if session_id not in self._sessions:
            return None

        session, expires_at = self._sessions[session_id]
        if datetime.utcnow() > expires_at:
            del self._sessions[session_id]
            return None

        return session

    async def delete_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    async def save_auth_state(self, state: str, auth_state: AuthState, ttl_seconds: int) -> None:
        expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        self._auth_states[state] = (auth_state, expires_at)

    async def get_auth_state(self, state: str) -> AuthState | None:
        if state not in self._auth_states:
            return None

        auth_state, expires_at = self._auth_states[state]
        if datetime.utcnow() > expires_at:
            del self._auth_states[state]
            return None

        return auth_state

    async def delete_auth_state(self, state: str) -> None:
        self._auth_states.pop(state, None)


class RedisSessionStore(SessionStore):
    """Redis-backed session store for production."""

    def __init__(self, redis_url: str):
        import redis.asyncio as redis
        self._redis = redis.from_url(redis_url, decode_responses=True)
        self._session_prefix = "fprime:session:"
        self._auth_state_prefix = "fprime:auth_state:"

    async def save_session(self, session_id: str, session: UserSession, ttl_seconds: int) -> None:
        key = f"{self._session_prefix}{session_id}"
        await self._redis.setex(key, ttl_seconds, session.model_dump_json())

    async def get_session(self, session_id: str) -> UserSession | None:
        key = f"{self._session_prefix}{session_id}"
        data = await self._redis.get(key)
        if not data:
            return None
        return UserSession.model_validate_json(data)

    async def delete_session(self, session_id: str) -> None:
        key = f"{self._session_prefix}{session_id}"
        await self._redis.delete(key)

    async def save_auth_state(self, state: str, auth_state: AuthState, ttl_seconds: int) -> None:
        key = f"{self._auth_state_prefix}{state}"
        await self._redis.setex(key, ttl_seconds, auth_state.model_dump_json())

    async def get_auth_state(self, state: str) -> AuthState | None:
        key = f"{self._auth_state_prefix}{state}"
        data = await self._redis.get(key)
        if not data:
            return None
        return AuthState.model_validate_json(data)

    async def delete_auth_state(self, state: str) -> None:
        key = f"{self._auth_state_prefix}{state}"
        await self._redis.delete(key)


class SessionManager:
    """Manages user sessions and authentication state."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

        # Use Redis in production, in-memory for development
        if self.settings.redis_url and self.settings.is_production:
            self._store = RedisSessionStore(self.settings.redis_url)
        else:
            logger.warning("Using in-memory session store - not suitable for production")
            self._store = InMemorySessionStore()

    def generate_session_id(self) -> str:
        """Generate a secure random session ID."""
        return secrets.token_urlsafe(32)

    async def create_session(self, session: UserSession) -> str:
        """Create a new session and return the session ID."""
        session_id = self.generate_session_id()
        ttl = self.settings.session_expire_minutes * 60
        await self._store.save_session(session_id, session, ttl)
        logger.info(f"Created session for user {session.user_id}")
        return session_id

    async def get_session(self, session_id: str) -> UserSession | None:
        """Retrieve a session by ID."""
        return await self._store.get_session(session_id)

    async def refresh_session(self, session_id: str, session: UserSession) -> None:
        """Update session with refreshed tokens."""
        ttl = self.settings.session_expire_minutes * 60
        await self._store.save_session(session_id, session, ttl)

    async def delete_session(self, session_id: str) -> None:
        """Delete a session (logout)."""
        await self._store.delete_session(session_id)
        logger.info(f"Deleted session {session_id}")

    async def save_auth_state(self, auth_state: AuthState) -> None:
        """Save authentication state for CSRF protection."""
        await self._store.save_auth_state(auth_state.state, auth_state, ttl_seconds=600)

    async def validate_auth_state(self, state: str) -> AuthState | None:
        """Validate and retrieve authentication state."""
        auth_state = await self._store.get_auth_state(state)
        if auth_state:
            await self._store.delete_auth_state(state)
        return auth_state


# Singleton instance
_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """Get or create session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager