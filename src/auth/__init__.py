"""
Google OAuth authentication for AViD Journal.

Verifies Google Identity Services tokens and manages user sessions.
No passwords stored — everything goes through Google's JWT.

Flow:
    Browser → Google Sign-In button → popup → JWT credential
    Frontend → POST /api/auth/google { credential: "..." }
    Backend → verify with Google → create/update user → return session
"""

from __future__ import annotations

import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from typing import Optional

import requests

logger = logging.getLogger(__name__)

GOOGLE_CLIENT_ID = os.environ.get(
    "GOOGLE_CLIENT_ID", ""
)
GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"


@dataclass
class GoogleUser:
    """User info extracted from a verified Google token."""

    google_id: str
    email: str
    name: str
    picture: str = ""
    email_verified: bool = False

    @classmethod
    def from_tokeninfo(cls, data: dict) -> "GoogleUser":
        return cls(
            google_id=data.get("sub", ""),
            email=data.get("email", ""),
            name=data.get("name", ""),
            picture=data.get("picture", ""),
            email_verified=data.get("email_verified", False),
        )


@dataclass
class Session:
    """Server-side session after successful Google login."""

    token: str
    user: GoogleUser
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 86400)  # 24h

    def is_expired(self) -> bool:
        return time.time() > self.expires_at


# ── In-memory session store (replace with Redis/DB for multi-process) ──────

_sessions: dict[str, Session] = {}


def verify_google_token(credential: str) -> Optional[GoogleUser]:
    """Verify a Google Identity Services credential JWT.

    Calls Google's tokeninfo endpoint. Does NOT require a client secret
    (the credential is already signed by Google; we just verify it's valid).

    Args:
        credential: The JWT string from Google's Sign-In button callback.

    Returns:
        GoogleUser if valid, None otherwise.
    """
    if not credential:
        return None

    try:
        resp = requests.get(
            GOOGLE_TOKENINFO_URL,
            params={"id_token": credential},
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning(f"Google tokeninfo failed: HTTP {resp.status_code}")
            return None

        data = resp.json()

        # Verify audience matches our client ID
        if GOOGLE_CLIENT_ID and data.get("aud") != GOOGLE_CLIENT_ID:
            logger.warning("Token audience mismatch")
            return None

        if not data.get("email_verified"):
            logger.warning("Email not verified")
            return None

        return GoogleUser.from_tokeninfo(data)

    except Exception as e:
        logger.exception(f"Google token verification failed: {e}")
        return None


def create_session(user: GoogleUser) -> Session:
    """Create a new session for an authenticated user.

    Generates a random session token and stores the session in memory.
    Returns the session object (token can be sent as a cookie to the client).
    """
    token = secrets.token_urlsafe(32)
    session = Session(token=token, user=user)
    _sessions[token] = session
    return session


def get_session(token: str) -> Optional[Session]:
    """Retrieve and validate a session by token.

    Returns None if the session doesn't exist or is expired.
    Expired sessions are automatically cleaned up.
    """
    session = _sessions.get(token)
    if session is None:
        return None
    if session.is_expired():
        del _sessions[token]
        return None
    return session


def delete_session(token: str) -> None:
    """Delete a session (logout)."""
    _sessions.pop(token, None)
