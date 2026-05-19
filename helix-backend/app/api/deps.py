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


async def helix_auth_gate(request: Request) -> None:
    """Optional API key gate for hosted demos (skipped for `/api/health` and JWT auth routes)."""
    path = request.url.path.rstrip("/") or "/"
    if path.endswith("/health"):
        return
    if path.startswith("/api/auth"):
        return
    expected = get_settings().helix_api_key.strip()
    if not expected:
        return
    got = request.headers.get("x-helix-key") or ""
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        got = auth[7:].strip()
    if got != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing Helix API key")


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
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
