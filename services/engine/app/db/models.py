"""ORM models (SQLAlchemy 2.0 typed declarative).

Phase 2 tables: settings, secrets, symbols, quotes_cache. Later phases add
watchlists, holdings, news, alerts, ai_reports — each in its own module-owned set.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Float, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UTCDateTime, timestamp_column, utcnow


class SettingRow(Base):
    """Key/value application settings (JSON values)."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[Any] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utcnow, onupdate=utcnow, nullable=False
    )


class SecretRow(Base):
    """Encrypted provider API keys. ``ciphertext`` is Fernet-encrypted; the
    plaintext never leaves the engine."""

    __tablename__ = "secrets"

    provider: Mapped[str] = mapped_column(String(64), primary_key=True)
    ciphertext: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = timestamp_column()
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utcnow, onupdate=utcnow, nullable=False
    )


class SymbolRow(Base):
    """The tradable-symbol universe (BIST + US), used for fast local search."""

    __tablename__ = "symbols"

    symbol: Mapped[str] = mapped_column(String(32), primary_key=True)
    display_symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    exchange: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    asset_type: Mapped[str] = mapped_column(String(16), nullable=False, default="EQUITY")
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    sector: Mapped[str | None] = mapped_column(String(128), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="seed")
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utcnow, onupdate=utcnow, nullable=False
    )


# Composite index to accelerate prefix search on the display symbol within an exchange.
Index("ix_symbols_display_exchange", SymbolRow.display_symbol, SymbolRow.exchange)


class QuoteCacheRow(Base):
    """Last-known quote snapshot per symbol (write-through persistence)."""

    __tablename__ = "quotes_cache"

    symbol: Mapped[str] = mapped_column(String(32), primary_key=True)
    payload: Mapped[Any] = mapped_column(JSON, nullable=False)
    fetched_at: Mapped[datetime] = timestamp_column()


# ---------------------------------------------------------------------------
# Phase 4 — Watchlists & Portfolio
# ---------------------------------------------------------------------------


class WatchlistRow(Base):
    """A named, ordered watchlist (a user can keep several)."""

    __tablename__ = "watchlists"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    position: Mapped[int] = mapped_column(default=0, nullable=False)
    created_at: Mapped[datetime] = timestamp_column()
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    items: Mapped[list[WatchlistItemRow]] = relationship(
        back_populates="watchlist",
        cascade="all, delete-orphan",
        order_by="WatchlistItemRow.position",
        passive_deletes=True,
    )


class WatchlistItemRow(Base):
    """A symbol belonging to a watchlist (unique per list, ordered)."""

    __tablename__ = "watchlist_items"
    __table_args__ = (
        UniqueConstraint("watchlist_id", "symbol", name="uq_watchlist_symbol"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    watchlist_id: Mapped[int] = mapped_column(
        ForeignKey("watchlists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    position: Mapped[int] = mapped_column(default=0, nullable=False)
    created_at: Mapped[datetime] = timestamp_column()

    watchlist: Mapped[WatchlistRow] = relationship(back_populates="items")


class HoldingRow(Base):
    """A single portfolio position/lot (multiple lots per symbol allowed)."""

    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    avg_cost: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    purchase_date: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    target_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = timestamp_column()
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utcnow, onupdate=utcnow, nullable=False
    )


# ---------------------------------------------------------------------------
# Phase 5 — News
# ---------------------------------------------------------------------------


class NewsRow(Base):
    """An aggregated news article. ``url`` is unique and serves as the dedup key."""

    __tablename__ = "news"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True, index=True)
    summary: Mapped[str | None] = mapped_column(String, nullable=True)
    symbols: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    published_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime, nullable=True, index=True
    )
    fetched_at: Mapped[datetime] = timestamp_column()


# ---------------------------------------------------------------------------
# Phase 6 — AI
# ---------------------------------------------------------------------------


class AiReportRow(Base):
    """A persisted AI stock-analysis report (history of generated analyses)."""

    __tablename__ = "ai_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    sentiment: Mapped[str] = mapped_column(String(16), nullable=False, default="neutral")
    payload: Mapped[Any] = mapped_column(JSON, nullable=False)  # serialized AnalysisReport
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utcnow, nullable=False, index=True
    )


# ---------------------------------------------------------------------------
# Phase 7 — Alerts & Notifications
# ---------------------------------------------------------------------------


class AlertRow(Base):
    """A user-defined price/technical alert condition on one symbol."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    params: Mapped[Any] = mapped_column(JSON, nullable=True)  # e.g. {"fast":50,"slow":200}
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    cooldown_seconds: Mapped[int] = mapped_column(default=3600, nullable=False)
    note: Mapped[str | None] = mapped_column(String(256), nullable=True)
    last_triggered_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    created_at: Mapped[datetime] = timestamp_column()
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utcnow, onupdate=utcnow, nullable=False
    )


# ---------------------------------------------------------------------------
# Phase 8 — Scheduler & Reports
# ---------------------------------------------------------------------------


class ScheduledReportRow(Base):
    """A persisted scheduled report (morning summary, stocks-to-watch, …)."""

    __tablename__ = "scheduled_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    payload: Mapped[Any] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utcnow, nullable=False, index=True
    )


class AlertEventRow(Base):
    """A record of an alert firing (the triggered-events feed / history)."""

    __tablename__ = "alert_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[int | None] = mapped_column(
        ForeignKey("alerts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str] = mapped_column(String(512), nullable=False)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utcnow, nullable=False, index=True
    )
