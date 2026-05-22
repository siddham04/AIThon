from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from ..config import get_settings

ALGORITHM = "HS256"
DEFAULT_ACCESS_EXPIRE_MINUTES = 60 * 24 * 7


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(
        plain.encode("utf-8"),
        hashed.encode("utf-8"),
    )


def _access_expire_minutes() -> int:
    return max(15, int(get_settings().helix_jwt_expire_minutes or DEFAULT_ACCESS_EXPIRE_MINUTES))


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    """Issue JWT. Rotate HELIX_JWT_SECRET in production to invalidate all sessions."""
    s = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": now + timedelta(minutes=_access_expire_minutes()),
        "iat": int(now.timestamp()),
        "jti": secrets.token_urlsafe(16),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, s.jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any] | None:
    s = get_settings()
    try:
        return jwt.decode(token, s.jwt_secret, algorithms=[ALGORITHM])
    except JWTError:
        return None
