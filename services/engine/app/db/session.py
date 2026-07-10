"""Database engine, session factory, and schema initialization.

Uses a synchronous SQLAlchemy engine over SQLite. For a single-user desktop app
this is robust and simple; SQLite operations are sub-millisecond, and FastAPI
runs sync route handlers in a threadpool so the event loop is never blocked.

Schema is managed by Alembic. ``init_db`` runs ``alembic upgrade head`` on
startup so a fresh install (or an upgraded app) always lands on the latest schema.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def _create_engine() -> Engine:
    settings = get_settings()
    engine = create_engine(
        settings.database_url,
        echo=False,
        future=True,
        connect_args={"check_same_thread": False},
    )

    # Enable WAL + foreign keys for concurrency and integrity on SQLite.
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_conn, _record):  # noqa: ANN001
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

    return engine


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = _create_engine()
    return _engine


def get_sessionmaker() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(), autoflush=False, expire_on_commit=False, future=True
        )
    return _SessionLocal


def get_session() -> Session:
    """Create a new session. Callers are responsible for closing/committing,
    or use the :func:`session_scope` context manager."""
    return get_sessionmaker()()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional scope: commits on success, rolls back on error, always closes."""
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _engine_root() -> Path:
    """Return the engine project root (dev tree or PyInstaller bundle root)."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[2]


def init_db() -> None:
    """Apply Alembic migrations to bring the database to ``head``."""
    from alembic.config import Config

    from alembic import command

    engine_dir = _engine_root()
    alembic_ini = engine_dir / "alembic.ini"
    settings = get_settings()

    cfg = Config(str(alembic_ini))
    cfg.set_main_option("script_location", str(engine_dir / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)

    logger.info("Running database migrations…")
    command.upgrade(cfg, "head")
    logger.info("Database ready at %s", settings.database_url)
