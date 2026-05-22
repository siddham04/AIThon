"""One-shot dev conveniences run at API startup (idempotent)."""
from __future__ import annotations

import logging

from sqlalchemy import select

from .config import get_settings
from .database import SessionLocal
from .services.security import hash_password
from .services.showcase_project import ensure_showcase_project
from .sqla_models import User

log = logging.getLogger("helix.bootstrap")

_INSECURE_JWT_DEFAULT = "change-me-in-production-use-openssl-rand"


def warn_insecure_jwt_secret() -> None:
    """Refuse startup when the default JWT secret is still in use."""
    s = get_settings()
    secret = (s.jwt_secret or "").strip()
    if secret != _INSECURE_JWT_DEFAULT:
        if len(secret) < 32:
            log.warning("JWT_SECRET is shorter than 32 chars — use a long random value in production")
        return

    msg = (
        "JWT_SECRET is the insecure default — set JWT_SECRET in .env "
        "(openssl rand -hex 32) before any public deploy"
    )
    if s.helix_production:
        raise RuntimeError(msg)
    if not s.helix_allow_insecure_jwt:
        raise RuntimeError(
            f"{msg} — or set HELIX_ALLOW_INSECURE_JWT=1 for local hackathon dev only"
        )
    log.critical(msg)


def ensure_demo_user() -> None:
    """Create the seeded demo account if missing (local `run.ps1` does not run scripts/seed.py)."""
    s = get_settings()
    email = (s.helix_demo_email or "").strip()
    password = s.helix_demo_password or ""
    if not email or not password:
        log.warning("HELIX_DEMO_EMAIL / HELIX_DEMO_PASSWORD empty; skip demo user bootstrap")
        return
    db = SessionLocal()
    try:
        exists = db.scalars(select(User).where(User.email == email)).first()
        if exists:
            return
        db.add(User(email=email, hashed_password=hash_password(password)))
        db.commit()
        log.info("Created demo user %s (from HELIX_DEMO_* env)", email)
        if s.helix_production:
            log.warning(
                "HELIX_DEMO_* credentials exist in production — rotate password or disable seeding"
            )
    finally:
        db.close()


def ensure_showcase_on_startup() -> None:
    """Pre-bake proj_* delivery package if missing (backup when live SSE stalls)."""
    s = get_settings()
    email = (s.helix_demo_email or "").strip()
    if not email:
        return
    db = SessionLocal()
    try:
        user = db.scalars(select(User).where(User.email == email)).first()
        if user is None:
            return
        pid = ensure_showcase_project(db)
        if pid:
            log.info(
                "Showcase backup ready: %s → /project/%s/ai-workspace",
                pid,
                pid,
            )
    except Exception:
        log.exception("Showcase bootstrap failed")
    finally:
        db.close()
