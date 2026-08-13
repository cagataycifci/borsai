"""Test fixtures: isolate each run in a fresh temp data dir and DB."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    """Point the engine at a throwaway data dir + disable network seeding, then
    reset cached singletons so the temp DB/engine are used."""
    monkeypatch.setenv("BORSA_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("BORSA_AUTO_SEED", "false")
    monkeypatch.setenv("BORSA_SCHEDULER_ENABLED", "false")

    # Reset config + DB singletons so they pick up the temp dir.
    from app.core import config as config_mod
    from app.core import security as security_mod
    from app.db import session as session_mod

    config_mod.get_settings.cache_clear()
    session_mod._engine = None
    session_mod._SessionLocal = None
    security_mod._box = None

    yield

    config_mod.get_settings.cache_clear()
    session_mod._engine = None
    session_mod._SessionLocal = None
    security_mod._box = None


@pytest.fixture
def initialized_db(isolated_env):
    from app.db.session import init_db

    init_db()
