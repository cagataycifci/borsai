"""HTTP tests for scheduler & reports API (fake market, no network)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.api.deps import get_report_service
from app.data.base import Interval, Range
from app.data.models import Candle, Quote
from app.data.service import MarketDataService
from app.main import create_app
from app.news import NewsItem, NewsService
from app.portfolio.schemas import HoldingCreate
from app.portfolio.service import PortfolioService
from app.scheduler import ReportService
from app.settings.service import SecretsService, SettingsService
from app.watchlists.service import WatchlistService


class _FakeAdapter:
    name = "fake"

    async def get_quote(self, symbol: str) -> Quote:
        base = 100.0
        bump = {"SPY": 2.5, "ASELS.IS": -1.2}.get(symbol.upper(), 0.5)
        return Quote(
            symbol=symbol.upper(),
            display_symbol=symbol.upper().replace(".IS", ""),
            name=f"{symbol} Inc",
            price=base + bump,
            change=bump,
            change_percent=bump,
        )

    async def search(self, query: str) -> list:
        return []

    async def get_history(
        self, symbol: str, interval: Interval, range_: Range
    ) -> list[Candle]:
        base = datetime(2025, 1, 1, tzinfo=UTC)
        return [
            Candle(
                time=base + timedelta(days=i),
                open=100,
                high=101,
                low=99,
                close=100 + i * 0.1,
                volume=1000,
            )
            for i in range(30)
        ]

    async def get_fundamentals(self, symbol: str):
        return None


class _FakeSource:
    name = "Fake"

    async def fetch(self) -> list[NewsItem]:
        return [
            NewsItem(
                source="Fake",
                title="Markets open higher",
                url="https://ex.com/1",
            )
        ]


def _report_service() -> ReportService:
    market = MarketDataService([_FakeAdapter()])
    news = NewsService(sources=[_FakeSource()])
    watchlists = WatchlistService()
    watchlists.ensure_default()
    portfolio = PortfolioService()
    portfolio.add(
        HoldingCreate(symbol="AAPL", quantity=10, avg_cost=150, currency="USD")
    )
    return ReportService(
        market,
        news,
        watchlists,
        portfolio,
        SettingsService(),
        SecretsService(),
    )


def test_scheduler_reports_and_calendar(initialized_db) -> None:
    app = create_app()
    app.dependency_overrides[get_report_service] = _report_service
    with TestClient(app) as client:
        # Scheduler status (disabled in tests but manager exists).
        status = client.get("/api/v1/scheduler/status").json()
        assert status["running"] is False
        assert isinstance(status["jobs"], list)

        # Generate + fetch morning summary.
        gen = client.post("/api/v1/reports/morning/generate?region=us").json()
        assert gen["region"] == "us"
        assert gen["benchmarks"]
        assert gen["overview"]

        cached = client.get("/api/v1/reports/morning?region=us").json()
        assert cached["overview"] == gen["overview"]

        # Stocks to watch digest.
        watch = client.post("/api/v1/reports/watch/generate").json()
        assert watch["picks"]
        assert any(p["symbol"] for p in watch["picks"])

        # Economic calendar.
        cal = client.get("/api/v1/calendar?days=14").json()
        assert len(cal["events"]) >= 1
        assert cal["events"][0]["title"]
