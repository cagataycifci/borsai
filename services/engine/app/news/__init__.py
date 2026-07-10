"""News layer (Phase 5): provider-agnostic sources + aggregation + storage."""

from app.news.parser import parse_feed
from app.news.schemas import NewsArticle, NewsItem
from app.news.service import NewsService
from app.news.sources import DEFAULT_SOURCES, RssNewsSource, YahooSymbolNews

__all__ = [
    "DEFAULT_SOURCES",
    "NewsArticle",
    "NewsItem",
    "NewsService",
    "RssNewsSource",
    "YahooSymbolNews",
    "parse_feed",
]
