"""News domain models + API schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class NewsItem(BaseModel):
    """A freshly-parsed article, before persistence (no id)."""

    source: str
    title: str
    url: str  # canonical link; also the dedup key
    summary: str | None = None
    symbols: list[str] = []
    published_at: datetime | None = None


class NewsArticle(BaseModel):
    """A stored article returned by the API."""

    id: int
    source: str
    title: str
    url: str
    summary: str | None
    symbols: list[str]
    published_at: datetime | None
