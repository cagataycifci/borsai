"""API integration test for the indicators endpoint (full HTTP + JSON path).

Uses a fake adapter so the test is offline and deterministic, and asserts the
response is valid JSON (NaN warm-up values must serialize as null, never NaN).
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
                open=float(i + 1),
                high=float(i + 2),
                low=float(i),
                close=float(i + 1),
                volume=1000.0,
            )
            for i in range(60)
        ]

    async def get_fundamentals(self, symbol: str) -> Fundamentals | None:
        return None


def test_indicators_endpoint_returns_json_safe_series(initialized_db) -> None:
    app = create_app()
    app.dependency_overrides[get_market_data] = lambda: MarketDataService([_FakeAdapter()])

    with TestClient(app) as client:
        resp = client.get(
            "/api/v1/indicators/TEST",
            params={"indicators": "sma:20,rsi,macd", "interval": "1d", "range": "1y"},
        )
        assert resp.status_code == 200
        body = resp.json()  # raises if NaN leaked into the payload
        keys = {s["key"] for s in body["series"]}
        assert "sma_20" in keys
        assert "rsi_14" in keys
        assert "macd" in keys

        sma = next(s for s in body["series"] if s["key"] == "sma_20")
        # First 19 points are warm-up nulls; later points are real numbers.
        assert sma["points"][0]["value"] is None
        assert sma["points"][-1]["value"] is not None
