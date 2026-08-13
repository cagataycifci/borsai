"""HTTP tests for commentator API (fake AI + news)."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi.testclient import TestClient

from app.ai import AIService
from app.api.deps import get_commentator_service
from app.commentator import CommentatorService
from app.data.models import Quote
from app.data.service import MarketDataService
from app.main import create_app
from app.news import NewsItem, NewsService
from app.settings.service import SecretsService, SettingsService


class _FakeProvider:
    name = "fake"
    model = "fake-1"

    async def complete(self, system: str, prompt: str, *, max_tokens: int = 2048) -> str:
        return json.dumps(
            [{"index": 0, "sentiment": "bullish", "importance": 4, "rationale": "strong"}]
        )

    async def stream(self, messages, *, system=None, max_tokens=2048) -> AsyncIterator[str]:
        yield "ok"

    async def aclose(self) -> None:
        return None


class _FakeAdapter:
    name = "fake"

    async def get_quote(self, symbol: str) -> Quote:
        return Quote(symbol=symbol.upper(), display_symbol=symbol.upper(), name="Co", price=1.0)

    async def search(self, query: str) -> list:
        return []

    async def get_history(self, symbol, interval, range_):
        return []

    async def get_fundamentals(self, symbol):
        return None


class _FakeSymbolSource:
    async def fetch_for(self, symbol: str) -> list[NewsItem]:
        return [
            NewsItem(
                source="CNBC",
                title=f"{symbol} rallies",
                url="https://ex.com/1",
                symbols=[symbol.upper()],
            )
        ]


def _commentator_service() -> CommentatorService:
    market = MarketDataService([_FakeAdapter()])
    news = NewsService(sources=[], symbol_source=_FakeSymbolSource())
    ai = AIService(
        SettingsService(),
        SecretsService(),
        market,
        news,
        lambda s, sec: _FakeProvider(),
    )
    return CommentatorService(news, ai)


def test_commentator_consensus(initialized_db) -> None:
    app = create_app()
    app.dependency_overrides[get_commentator_service] = _commentator_service
    with TestClient(app) as client:
        report = client.get("/api/v1/commentator/AAPL").json()
        assert report["symbol"] == "AAPL"
        assert report["consensus"] in {"bullish", "bearish", "neutral", "mixed"}
        assert len(report["opinions"]) == 1
        assert report["opinions"][0]["source"] == "CNBC"
