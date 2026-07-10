"""Application configuration.

Settings are loaded from environment variables (prefixed ``BORSA_``) and an
optional ``.env`` file. The app data directory (database, logs) is resolved to a
per-OS user location so the packaged app writes to a sane, writable place.
"""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_data_dir() -> Path:
    """Return the per-user application data directory, creating it if needed."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    path = base / "BorsaAI"
    path.mkdir(parents=True, exist_ok=True)
    return path


class Settings(BaseSettings):
    """Strongly-typed application settings."""

    model_config = SettingsConfigDict(
        env_prefix="BORSA_",
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Borsa AI Terminal Engine"
    environment: str = "development"

    engine_host: str = "127.0.0.1"
    engine_port: int = 8787
    log_level: str = "INFO"

    # Seed the symbol universe on first run. Disabled in tests to avoid network.
    auto_seed: bool = True

    # Background scheduler (APScheduler). Disabled in tests.
    scheduler_enabled: bool = True

    # Comma-separated origins allowed to call the engine. The Electron renderer
    # serves from a file:// or dev http origin; loopback only by design.
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    data_dir: Path = Field(default_factory=_default_data_dir)

    # Default cache TTLs (seconds).
    quote_cache_ttl: float = 10.0
    search_cache_ttl: float = 3600.0

    @property
    def database_url(self) -> str:
        return f"sqlite:///{(self.data_dir / 'borsa.db').as_posix()}"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
