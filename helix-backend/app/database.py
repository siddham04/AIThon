"""SQLAlchemy engine and session factory."""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
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


# Enable WAL + a busy timeout for SQLite. Without this, concurrent demo
# runs (e.g. seed.py upserting `proj_demo_seed01` while a /api/demo/run
# is persisting) can raise `sqlite3.OperationalError: database is
# locked` mid-stream. WAL allows readers and one writer to coexist and
# the busy_timeout makes other writers wait briefly instead of erroring
# immediately.
@event.listens_for(Engine, "connect")
def _sqlite_pragmas(dbapi_connection, _connection_record):  # pragma: no cover - infra glue
    if not str(getattr(dbapi_connection, "filename", "")):
        # Some DBAPIs do not expose a .filename attribute; fall through
        # to the dialect check below.
        pass
    try:
        # Only apply PRAGMAs to SQLite connections. Other dialects do
        # not implement these statements and would raise.
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=5000")
        finally:
            cursor.close()
    except Exception:
        # Non-SQLite drivers will raise here — silently ignore. We
        # never want this hook to break engine creation for PG/MySQL.
        pass


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
