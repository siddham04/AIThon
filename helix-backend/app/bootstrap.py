"""One-shot dev conveniences run at API startup (idempotent)."""
from __future__ import annotations

import logging

from sqlalchemy import select

from .config import get_settings
from .database import SessionLocal
from .services.security import hash_password
from .sqla_models import User

log = logging.getLogger("helix.bootstrap")


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
    finally:
        db.close()
