"""Shared FastAPI dependencies."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..services.security import decode_token
from ..sqla_models import User

security = HTTPBearer(auto_error=False)

# Paths that work without Authorization (guest login + health + static demo metadata).
_PUBLIC_API_PATHS = frozenset({
    "/api/health",
    "/health",
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/guest",
    "/api/auth/refresh",
    "/api/demo/steps",
    "/api/demo/showcase",
})


async def helix_auth_gate(request: Request) -> None:
    """Require JWT on all /api routes except auth, health, and demo metadata.

    Service automation may use ``X-Helix-Key`` when ``HELIX_API_KEY`` is set.
    Do not accept the service key via ``Authorization: Bearer`` (same header as JWT).
    """
    path = request.url.path.rstrip("/") or "/"
    if path in _PUBLIC_API_PATHS or path.endswith("/health"):
        return
    if path.startswith("/api/auth/"):
        return

    if not path.startswith("/api/"):
        return

    settings = get_settings()
    expected_key = settings.helix_api_key.strip()
    service_key = (request.headers.get("x-helix-key") or "").strip()
    if expected_key and service_key == expected_key:
        return

    auth = request.headers.get("authorization") or ""
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = auth[7:].strip()
    if expected_key and token == expected_key:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Use X-Helix-Key for service auth, not Authorization Bearer",
        )
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    settings = get_settings()
    expected_key = settings.helix_api_key.strip()
    if expected_key and creds.credentials == expected_key:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Service API key cannot be used as a user session token",
        )
    payload = decode_token(creds.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )
    try:
        uid = int(payload["sub"])
    except (TypeError, ValueError):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject"
        )
    user = db.get(User, uid)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
