"""HTTP tests for the AI API using a fake provider (no network, no API key)."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

from app.ai import AIService
from app.api.deps import get_ai_service
from app.data.base import Interval, Range
from app.data.models import Candle, Quote
from app.data.service import MarketDataService
from app.main import create_app
from app.news import NewsItem, NewsService
from app.settings.service import SecretsService, SettingsService
from fastapi.testclient import TestClient


class _FakeAdapter:
    name = "fake"

    async def get_quote(self, symbol: str) -> Quote:
        return Quote(
            symbol=symbol,
            display_symbol=symbol,
            name="Fake Co",
            price=100.0,
            change=1.5,
            change_percent=1.5,
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
                open=100 + i,
                high=101 + i,
                low=99 + i,
                close=100 + i,
                volume=1000 + i,
            )
            for i in range(60)
        ]

    async def get_fundamentals(self, symbol: str):
        return None


class _FakeProvider:
    name = "fake"
    model = "fake-1"

    async def complete(self, system: str, prompt: str, *, max_tokens: int = 2048) -> str:
        if "classify" in system.lower():
            return json.dumps(
                [{"index": 0, "sentiment": "bullish", "importance": 4, "rationale": "ok"}]
            )
        return json.dumps(
            {
                "sentiment": "bullish",
                "rating": 4,
                "summary": "Looks constructive.",
                "key_points": ["momentum up", "volume rising"],
                "risks": ["macro headwinds"],
                "technical_outlook": "Above the 50-day SMA.",
                "recommendation": "Informational only.",
            }
        )

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        system: str | None = None,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        for chunk in ["Hello", " from", " the AI"]:
            yield chunk

    async def aclose(self) -> None:
        return None


class _FakeSymbolSource:
    async def fetch_for(self, symbol: str) -> list[NewsItem]:
        sym = symbol.upper()
        return [
            NewsItem(
                source="Fake", title=f"{sym} beats earnings",
                url=f"https://ex.com/{sym}", symbols=[sym],
            )
        ]


class _FakeSource:
    name = "Fake"

    async def fetch(self) -> list[NewsItem]:
        return [NewsItem(source="Fake", title="Market rallies", url="https://ex.com/1")]


def _ai_service() -> AIService:
    market = MarketDataService([_FakeAdapter()])
    news = NewsService(sources=[_FakeSource()], symbol_source=_FakeSymbolSource())
    return AIService(
        SettingsService(),
        SecretsService(),
        market,
        news,
        lambda settings, secrets: _FakeProvider(),
    )


def test_ai_status_and_provider_select(initialized_db) -> None:
    app = create_app()
    app.dependency_overrides[get_ai_service] = _ai_service
    with TestClient(app) as client:
        status = client.get("/api/v1/ai/status").json()
        assert status["active_provider"] == "anthropic"  # default
        assert set(status["providers"]) >= {"anthropic", "openai", "gemini", "ollama"}
        assert status["configured"]["anthropic"] is False  # no key in tests

        # Selecting Ollama (keyless) flips readiness on.
        out = client.put(
            "/api/v1/ai/provider", json={"active_provider": "ollama"}
        ).json()
        assert out["active_provider"] == "ollama"
        assert out["ready"] is True

        # Unknown provider rejected.
        assert (
            client.put("/api/v1/ai/provider", json={"active_provider": "nope"}).status_code
            == 400
        )


def test_ai_analyze_persist_and_classify(initialized_db) -> None:
    app = create_app()
    app.dependency_overrides[get_ai_service] = _ai_service
    with TestClient(app) as client:
        report = client.post("/api/v1/ai/analyze", json={"symbol": "aapl"}).json()
        assert report["symbol"] == "AAPL"
        assert report["sentiment"] == "bullish"
        assert report["rating"] == 4
        assert report["key_points"]

        # Persisted — the latest report is retrievable.
        stored = client.get("/api/v1/ai/reports/AAPL").json()
        assert stored["summary"] == report["summary"]
        assert client.get("/api/v1/ai/reports/ZZZZ").status_code == 404

        # News classification for the symbol.
        verdicts = client.post(
            "/api/v1/ai/classify", json={"symbol": "aapl", "limit": 5}
        ).json()
        assert len(verdicts) == 1
        assert verdicts[0]["sentiment"] == "bullish"
        assert verdicts[0]["importance"] == 4


def test_ai_chat_streams_sse(initialized_db) -> None:
    app = create_app()
    app.dependency_overrides[get_ai_service] = _ai_service
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/ai/chat",
            json={"messages": [{"role": "user", "content": "hi"}]},
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        body = resp.text
        assert "Hello" in body
        assert "[DONE]" in body
