"""Market data service.

Composes an ordered list of :class:`MarketDataAdapter` instances with a
fallback + TTL-cache policy. Call sites depend only on this service, never on a
concrete provider, so adding a paid real-time provider later is purely additive
(prepend it to the adapter list).
"""

from __future__ import annotations

from typing import Protocol

from app.core.cache import TTLCache
from app.core.config import get_settings
from app.core.logging import get_logger
from app.data.base import Interval, MarketDataAdapter, Range
from app.data.models import Candle, Fundamentals, Quote, SymbolRef
from app.technical import resample_candles

logger = get_logger(__name__)


class QuoteStore(Protocol):
    """Optional persistence for the latest quote per symbol."""

    def upsert(self, quote: Quote) -> None: ...
    def get(self, symbol: str) -> Quote | None: ...


class MarketDataService:
    def __init__(
        self, adapters: list[MarketDataAdapter], quote_store: QuoteStore | None = None
    ) -> None:
        if not adapters:
            raise ValueError("MarketDataService requires at least one adapter")
        self._adapters = adapters
        self._quote_store = quote_store
        settings = get_settings()
        self._quote_cache: TTLCache[Quote] = TTLCache(ttl=settings.quote_cache_ttl)
        self._search_cache: TTLCache[list[SymbolRef]] = TTLCache(
            ttl=settings.search_cache_ttl
        )

    @property
    def provider_names(self) -> list[str]:
        return [a.name for a in self._adapters]

    async def get_quote(self, symbol: str) -> Quote | None:
        symbol = self.normalize(symbol)

        async def fetch() -> Quote | None:
            for adapter in self._adapters:
                quote = await adapter.get_quote(symbol)
                if quote is not None:
                    if self._quote_store is not None:
                        self._quote_store.upsert(quote)
                    return quote
            # All providers failed — serve the last persisted snapshot if any.
            if self._quote_store is not None:
                return self._quote_store.get(symbol)
            return None

        return await self._quote_cache.get_or_set(symbol, fetch)

    async def search(self, query: str) -> list[SymbolRef]:
        query = query.strip()
        if not query:
            return []

        async def fetch() -> list[SymbolRef]:
            seen: set[str] = set()
            merged: list[SymbolRef] = []
            for adapter in self._adapters:
                for ref in await adapter.search(query):
                    if ref.symbol not in seen:
                        seen.add(ref.symbol)
                        merged.append(ref)
            return merged

        return await self._search_cache.get_or_set(query.lower(), fetch)

    async def get_history(
        self, symbol: str, interval: Interval, range_: Range
    ) -> list[Candle]:
        symbol = self.normalize(symbol)
        # No provider offers native 4h bars — fetch 1h and resample.
        if interval is Interval.H4:
            hourly = await self._fetch_history(symbol, Interval.H1, range_)
            return resample_candles(hourly, "4h")
        return await self._fetch_history(symbol, interval, range_)

    async def _fetch_history(
        self, symbol: str, interval: Interval, range_: Range
    ) -> list[Candle]:
        """Return the first non-empty candle series from the adapter chain."""
        for adapter in self._adapters:
            candles = await adapter.get_history(symbol, interval, range_)
            if candles:
                return candles
        return []

    async def get_fundamentals(self, symbol: str) -> Fundamentals | None:
        symbol = self.normalize(symbol)
        for adapter in self._adapters:
            fundamentals = await adapter.get_fundamentals(symbol)
            if fundamentals is not None:
                return fundamentals
        return None

    @staticmethod
    def normalize(symbol: str) -> str:
        """Normalize a user-entered symbol to the canonical internal form.

        BIST tickers are stored/queried with the yfinance ``.IS`` suffix. We do
        NOT auto-suffix bare tickers here (e.g. ``F`` is Ford, not a BIST stock);
        explicit BIST entry uses ``ASELS.IS`` or is resolved via search.
        """
        return symbol.strip().upper()
