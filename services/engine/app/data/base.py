"""Market data adapter abstraction.

Every concrete provider (yfinance, Finnhub, a paid real-time vendor, …)
implements :class:`MarketDataAdapter`. The :class:`MarketDataService` composes
adapters with a fallback + cache policy, so call sites never depend on a
specific provider. Swapping free→paid is purely additive.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol, runtime_checkable

from app.data.models import Candle, Fundamentals, Quote, SymbolRef


class Interval(StrEnum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1wk"
    MO1 = "1mo"


class Range(StrEnum):
    D1 = "1d"
    D5 = "5d"
    M1 = "1mo"
    M3 = "3mo"
    M6 = "6mo"
    Y1 = "1y"
    Y2 = "2y"
    Y5 = "5y"
    MAX = "max"


@runtime_checkable
class MarketDataAdapter(Protocol):
    """Contract every market-data provider must satisfy."""

    name: str

    async def get_quote(self, symbol: str) -> Quote | None: ...

    async def search(self, query: str) -> list[SymbolRef]: ...

    async def get_history(
        self, symbol: str, interval: Interval, range_: Range
    ) -> list[Candle]: ...

    async def get_fundamentals(self, symbol: str) -> Fundamentals | None: ...


class AdapterError(Exception):
    """Raised by adapters for recoverable provider failures."""
