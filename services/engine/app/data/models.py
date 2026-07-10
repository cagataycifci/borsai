"""Domain models for market data.

These Pydantic models are the canonical shapes returned by the data layer and
serialized over the API. The TypeScript renderer mirrors them in
``renderer/src/lib/contracts.ts``.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Exchange(StrEnum):
    BIST = "BIST"
    NYSE = "NYSE"
    NASDAQ = "NASDAQ"
    AMEX = "AMEX"
    OTHER = "OTHER"


class AssetType(StrEnum):
    EQUITY = "EQUITY"
    ETF = "ETF"
    INDEX = "INDEX"
    CRYPTO = "CRYPTO"
    OTHER = "OTHER"


class SymbolRef(BaseModel):
    """A lightweight reference to a tradable symbol (search results, lists)."""

    symbol: str  # canonical internal symbol (BIST uses the .IS suffix)
    display_symbol: str  # what the UI shows (bare ticker)
    name: str
    exchange: Exchange = Exchange.OTHER
    asset_type: AssetType = AssetType.EQUITY
    currency: str = "USD"


class Quote(BaseModel):
    """A point-in-time price snapshot plus common header metrics."""

    symbol: str
    display_symbol: str
    name: str | None = None
    exchange: Exchange = Exchange.OTHER
    currency: str = "USD"

    price: float | None = None
    previous_close: float | None = None
    open: float | None = None
    day_high: float | None = None
    day_low: float | None = None

    change: float | None = None
    change_percent: float | None = None

    volume: float | None = None
    market_cap: float | None = None

    pe_ratio: float | None = None
    eps: float | None = None
    dividend_yield: float | None = None

    week52_high: float | None = None
    week52_low: float | None = None

    sector: str | None = None
    industry: str | None = None

    source: str | None = None  # which adapter produced this
    as_of: datetime | None = None


class Candle(BaseModel):
    """A single OHLCV bar."""

    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


class Fundamentals(BaseModel):
    """Fundamental snapshot (expanded in Phase 2)."""

    symbol: str
    market_cap: float | None = None
    pe_ratio: float | None = None
    forward_pe: float | None = None
    eps: float | None = None
    dividend_yield: float | None = None
    beta: float | None = None
    profit_margin: float | None = None
    revenue: float | None = None
    sector: str | None = None
    industry: str | None = None
    extra: dict[str, float | str | None] = Field(default_factory=dict)
