"""HTTP tests for global search API."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.deps import get_global_search_service
from app.data.models import Quote
from app.data.service import MarketDataService
from app.db.repositories import SymbolRepository
from app.db.session import session_scope
from app.main import create_app
from app.search import GlobalSearchService


class _FakeAdapter:
    name = "fake"

    async def get_quote(self, symbol: str) -> Quote:
        return Quote(symbol=symbol, display_symbol=symbol, name="Co", price=1.0)

    async def search(self, query: str) -> list:
        return []

    async def get_history(self, symbol, interval, range_):
        return []

    async def get_fundamentals(self, symbol):
        return None


def _seed() -> None:
    rows = [
        {
            "symbol": "AAPL",
            "display_symbol": "AAPL",
            "name": "Apple Inc.",
            "exchange": "NASDAQ",
            "asset_type": "EQUITY",
            "currency": "USD",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "source": "test",
        },
        {
            "symbol": "MSFT",
            "display_symbol": "MSFT",
            "name": "Microsoft",
            "exchange": "NASDAQ",
            "asset_type": "EQUITY",
            "currency": "USD",
            "sector": "Technology",
            "industry": "Software",
            "source": "test",
        },
        {
            "symbol": "ASELS.IS",
            "display_symbol": "ASELS",
            "name": "Aselsan",
            "exchange": "BIST",
            "asset_type": "EQUITY",
            "currency": "TRY",
            "sector": "Industrials",
            "industry": "Defense",
            "source": "test",
        },
    ]
    with session_scope() as s:
        SymbolRepository(s).bulk_upsert(rows)


def _search_service() -> GlobalSearchService:
    from app.data.universe.service import SymbolUniverseService

    return GlobalSearchService(SymbolUniverseService(), MarketDataService([_FakeAdapter()]))


def test_global_search_symbols_and_facets(initialized_db) -> None:
    _seed()
    app = create_app()
    app.dependency_overrides[get_global_search_service] = _search_service
    with TestClient(app) as client:
        result = client.get("/api/v1/search/global?q=tech").json()
        assert result["query"] == "tech"
        assert any(s["display_symbol"] == "AAPL" for s in result["symbols"]) or result["facets"]
        facets = {f["kind"]: f for f in result["facets"]}
        if "sector" in facets:
            assert facets["sector"]["label"] == "Technology"
            syms = client.get("/api/v1/search/facet/sector/Technology").json()
            assert len(syms) >= 2

        country = client.get("/api/v1/search/global?q=turkey").json()
        assert any(f["kind"] == "country" for f in country["facets"])
