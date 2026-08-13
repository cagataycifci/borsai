"""HTTP tests for the news API (offline fake sources, real DB)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.deps import get_news_service
from app.main import create_app
from app.news import NewsItem, NewsService


class _FakeSource:
    name = "Fake"

    def __init__(self, items: list[NewsItem]) -> None:
        self._items = items

    async def fetch(self) -> list[NewsItem]:
        return self._items


class _FakeSymbolSource:
    async def fetch_for(self, symbol: str) -> list[NewsItem]:
        sym = symbol.upper()
        return [
            NewsItem(
                source="Fake",
                title=f"{sym} jumps",
                url=f"https://ex.com/{sym}",
                symbols=[sym],
            )
        ]


def _service() -> NewsService:
    items = [
        NewsItem(source="Fake", title="A", url="https://ex.com/1"),
        NewsItem(source="Fake", title="B", url="https://ex.com/2"),
    ]
    return NewsService(sources=[_FakeSource(items)], symbol_source=_FakeSymbolSource())


def test_news_flow(initialized_db) -> None:
    app = create_app()
    app.dependency_overrides[get_news_service] = _service

    with TestClient(app) as client:
        # Empty store → GET triggers a one-time refresh.
        body = client.get("/api/v1/news").json()
        assert len(body) == 2
        assert {a["title"] for a in body} == {"A", "B"}

        # Refreshing again stores nothing new (url dedup).
        assert client.post("/api/v1/news/refresh").json()["stored"] == 0

        # Per-symbol news (live-fetched, stored, tagged).
        arts = client.get("/api/v1/news/aapl").json()
        assert len(arts) >= 1
        assert "AAPL" in arts[0]["symbols"]

        # Pagination bounds are enforced.
        assert client.get("/api/v1/news", params={"limit": 1}).status_code == 200
        assert client.get("/api/v1/news", params={"limit": 0}).status_code == 422
