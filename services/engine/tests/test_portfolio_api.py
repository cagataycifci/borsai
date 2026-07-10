"""HTTP CRUD + live-P&L tests for the portfolio API (offline fake adapter)."""

from __future__ import annotations

from app.api.deps import get_market_data
from app.data.base import Interval, Range
from app.data.models import Candle, Fundamentals, Quote, SymbolRef
from app.data.service import MarketDataService
from app.main import create_app
from fastapi.testclient import TestClient


class _FakeAdapter:
    name = "fake"
    PRICES = {"AAPL": 150.0, "MSFT": 220.0}

    async def get_quote(self, symbol: str) -> Quote | None:
        price = self.PRICES.get(symbol.upper())
        if price is None:
            return None
        return Quote(
            symbol=symbol.upper(),
            display_symbol=symbol.upper(),
            price=price,
            change=2.0,
            currency="USD",
        )

    async def search(self, query: str) -> list[SymbolRef]:
        return []

    async def get_history(
        self, symbol: str, interval: Interval, range_: Range
    ) -> list[Candle]:
        return []

    async def get_fundamentals(self, symbol: str) -> Fundamentals | None:
        return None


def test_portfolio_crud_and_summary(initialized_db) -> None:
    app = create_app()
    app.dependency_overrides[get_market_data] = lambda: MarketDataService([_FakeAdapter()])

    with TestClient(app) as client:
        assert client.get("/api/v1/holdings").json() == []

        aapl = client.post(
            "/api/v1/holdings", json={"symbol": "aapl", "quantity": 10, "avg_cost": 100.0}
        ).json()
        assert aapl["symbol"] == "AAPL"  # normalized
        client.post(
            "/api/v1/holdings",
            json={"symbol": "MSFT", "quantity": 5, "avg_cost": 200.0, "currency": "usd"},
        )

        summary = client.get("/api/v1/portfolio").json()
        assert len(summary["positions"]) == 2
        pos = next(p for p in summary["positions"] if p["holding"]["symbol"] == "AAPL")
        assert pos["market_value"] == 1500.0
        assert pos["unrealized_pnl"] == 500.0
        assert pos["day_pnl"] == 20.0  # change 2.0 × qty 10

        totals = {t["currency"]: t for t in summary["totals"]}
        assert totals["USD"]["cost_basis"] == 2000.0
        assert totals["USD"]["market_value"] == 2600.0

        # Partial update.
        updated = client.put(
            f"/api/v1/holdings/{aapl['id']}", json={"quantity": 20}
        ).json()
        assert updated["quantity"] == 20
        assert updated["avg_cost"] == 100.0  # unchanged

        # Delete + 404s.
        assert client.delete(f"/api/v1/holdings/{aapl['id']}").status_code == 200
        assert client.delete("/api/v1/holdings/9999").status_code == 404
        assert client.put("/api/v1/holdings/9999", json={"quantity": 1}).status_code == 404
