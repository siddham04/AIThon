"""SQLAlchemy engine and session factory."""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings


def _connect_args(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def make_engine():
    s = get_settings()
    return create_engine(
        s.db_url,
        connect_args=_connect_args(s.db_url),
        pool_pre_ping=True,
    )


engine = make_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from . import sqla_models  # noqa: F401 — register ORM mappers

    from .sqla_models import Base

    Base.metadata.create_all(bind=engine)
