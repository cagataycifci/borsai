"""API integration test for the volume-profile endpoint (full HTTP + JSON path).

Uses a fake adapter so the test is offline and deterministic.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.api.deps import get_market_data
from app.data.base import Interval, Range
from app.data.models import Candle, Fundamentals, Quote, SymbolRef
from app.data.service import MarketDataService
from app.main import create_app


class _FakeAdapter:
    name = "fake"

    async def get_quote(self, symbol: str) -> Quote | None:
        return None

    async def search(self, query: str) -> list[SymbolRef]:
        return []

    async def get_history(
        self, symbol: str, interval: Interval, range_: Range
    ) -> list[Candle]:
        start = datetime(2026, 1, 1, tzinfo=UTC)
        return [
            Candle(
                time=start + timedelta(days=i),
                open=float(10 + i % 5),
                high=float(12 + i % 5),
                low=float(9 + i % 5),
                close=float(11 + i % 5),
                volume=1000.0,
            )
            for i in range(60)
        ]

    async def get_fundamentals(self, symbol: str) -> Fundamentals | None:
        return None


def test_volume_profile_endpoint(initialized_db) -> None:
    app = create_app()
    app.dependency_overrides[get_market_data] = lambda: MarketDataService([_FakeAdapter()])

    with TestClient(app) as client:
        resp = client.get(
            "/api/v1/volume-profile/TEST",
            params={"bins": 12, "interval": "1d", "range": "1y"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["bins"]) == 12
        assert body["poc"] is not None
        assert body["max_volume"] > 0
        # Exactly one Point of Control.
        assert sum(1 for b in body["bins"] if b["poc"]) == 1
        # Total volume is conserved (60 bars × 1000).
        assert round(sum(b["volume"] for b in body["bins"])) == 60_000
