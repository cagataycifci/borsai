"""Verifies write-through quote persistence and stale-fallback in the service."""

from __future__ import annotations

from app.data.models import Exchange, Quote


class FakeAdapter:
    name = "fake"

    def __init__(self) -> None:
        self.fail = False

    async def get_quote(self, symbol: str) -> Quote | None:
        if self.fail:
            return None
        return Quote(
            symbol=symbol,
            display_symbol=symbol,
            name="Fake Co",
            exchange=Exchange.NASDAQ,
            currency="USD",
            price=123.45,
            previous_close=120.0,
            source=self.name,
        )

    async def search(self, query):  # pragma: no cover - unused here
        return []

    async def get_history(self, symbol, interval, range_):  # pragma: no cover
        return []

    async def get_fundamentals(self, symbol):  # pragma: no cover
        return None


async def test_quote_is_persisted_and_served_when_providers_fail(initialized_db) -> None:
    from app.data.quote_store import SqliteQuoteStore
    from app.data.service import MarketDataService

    adapter = FakeAdapter()
    service = MarketDataService([adapter], quote_store=SqliteQuoteStore())

    # First fetch hits the adapter and persists.
    q1 = await service.get_quote("FAKE")
    assert q1 is not None and q1.price == 123.45

    # The snapshot is in quotes_cache.
    assert SqliteQuoteStore().get("FAKE").price == 123.45

    # Now the provider fails and the in-memory TTL has the value; force a new
    # service (fresh TTL cache) so it must rely on the persistent store.
    adapter.fail = True
    fresh = MarketDataService([adapter], quote_store=SqliteQuoteStore())
    stale = await fresh.get_quote("FAKE")
    assert stale is not None and stale.price == 123.45  # served from persistence
