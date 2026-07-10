"""News sources: generic RSS feeds + Yahoo Finance per-symbol headlines.

Each source is provider-agnostic and returns canonical :class:`NewsItem`s, so the
aggregation service can fan out across them uniformly (mirrors the data-adapter
pattern in ``app/data``). Network failures are the caller's concern — the service
isolates each source with ``asyncio.gather(return_exceptions=True)``.
"""

from __future__ import annotations

import httpx

from app.news.parser import parse_feed
from app.news.schemas import NewsItem

_UA = "BorsaAITerminal/0.1 (+https://localhost)"
_TIMEOUT = 10.0


async def _get(url: str) -> bytes:
    async with httpx.AsyncClient(
        timeout=_TIMEOUT, headers={"User-Agent": _UA}, follow_redirects=True
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.content


class RssNewsSource:
    """A general (market-wide) RSS/Atom feed."""

    def __init__(self, name: str, url: str) -> None:
        self.name = name
        self.url = url

    async def fetch(self) -> list[NewsItem]:
        return parse_feed(await _get(self.url), self.name)


class YahooSymbolNews:
    """Per-symbol headlines from Yahoo Finance's RSS endpoint."""

    name = "Yahoo Finance"

    async def fetch_for(self, symbol: str) -> list[NewsItem]:
        sym = symbol.strip().upper()
        url = (
            "https://feeds.finance.yahoo.com/rss/2.0/headline"
            f"?s={sym}&region=US&lang=en-US"
        )
        return parse_feed(await _get(url), self.name, symbols=[sym])


# Best-effort default market-news feeds (failures are isolated per source).
DEFAULT_SOURCES: list[RssNewsSource] = [
    RssNewsSource("Yahoo Finance", "https://finance.yahoo.com/news/rssindex"),
    RssNewsSource(
        "CNBC",
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
    ),
    RssNewsSource("MarketWatch", "http://feeds.marketwatch.com/marketwatch/topstories/"),
]
