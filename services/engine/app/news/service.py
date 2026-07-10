"""News aggregation service: fan out across sources, dedup, persist, query."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Protocol

from sqlalchemy import select

from app.core.logging import get_logger
from app.db.base import utcnow
from app.db.models import NewsRow
from app.db.session import session_scope
from app.news.schemas import NewsArticle, NewsItem
from app.news.sources import DEFAULT_SOURCES, YahooSymbolNews

logger = get_logger(__name__)


class _Source(Protocol):
    name: str

    async def fetch(self) -> list[NewsItem]: ...


class _SymbolSource(Protocol):
    async def fetch_for(self, symbol: str) -> list[NewsItem]: ...


class NewsService:
    def __init__(
        self,
        sources: Sequence[_Source] | None = None,
        symbol_source: _SymbolSource | None = None,
    ) -> None:
        self._sources = list(DEFAULT_SOURCES) if sources is None else list(sources)
        self._symbol_source = symbol_source or YahooSymbolNews()

    async def refresh(self) -> int:
        """Fetch all general sources concurrently; store new (deduped) articles."""
        results = await asyncio.gather(
            *(s.fetch() for s in self._sources), return_exceptions=True
        )
        items: list[NewsItem] = []
        for src, res in zip(self._sources, results, strict=True):
            if isinstance(res, BaseException):
                logger.warning("News source %s failed: %s", src.name, res)
            else:
                items.extend(res)
        return self._store(items)

    async def get_for_symbol(self, symbol: str, limit: int = 30) -> list[NewsArticle]:
        """Live-fetch per-symbol headlines (store for history), with a DB fallback."""
        items: list[NewsItem] = []
        try:
            items = await self._symbol_source.fetch_for(symbol)
        except Exception as exc:  # noqa: BLE001 (network is best-effort)
            logger.warning("Symbol news fetch failed for %s: %s", symbol, exc)

        if items:
            self._store(items)
            urls = [i.url for i in items]
            with session_scope() as s:
                rows = (
                    s.execute(
                        select(NewsRow)
                        .where(NewsRow.url.in_(urls))
                        .order_by(NewsRow.published_at.desc(), NewsRow.id.desc())
                        .limit(limit)
                    )
                    .scalars()
                    .all()
                )
                return [self._to_article(r) for r in rows]

        return self._recent_for_symbol(symbol, limit)

    def list_recent(self, limit: int = 50, offset: int = 0) -> list[NewsArticle]:
        with session_scope() as s:
            rows = (
                s.execute(
                    select(NewsRow)
                    .order_by(NewsRow.published_at.desc(), NewsRow.id.desc())
                    .limit(limit)
                    .offset(offset)
                )
                .scalars()
                .all()
            )
            return [self._to_article(r) for r in rows]

    def count(self) -> int:
        from sqlalchemy import func

        with session_scope() as s:
            return s.execute(select(func.count()).select_from(NewsRow)).scalar_one()

    # -- internals ----------------------------------------------------------
    def _store(self, items: list[NewsItem]) -> int:
        if not items:
            return 0
        # Dedup within the batch by url, then against what's already stored.
        batch = {it.url: it for it in items}
        now = utcnow()
        with session_scope() as s:
            existing = set(
                s.execute(
                    select(NewsRow.url).where(NewsRow.url.in_(list(batch)))
                )
                .scalars()
                .all()
            )
            fresh = [it for url, it in batch.items() if url not in existing]
            for it in fresh:
                s.add(
                    NewsRow(
                        source=it.source[:64],
                        title=it.title[:512],
                        url=it.url[:1024],
                        summary=it.summary,
                        symbols=it.symbols,
                        published_at=it.published_at,
                        fetched_at=now,
                    )
                )
            return len(fresh)

    def _recent_for_symbol(self, symbol: str, limit: int) -> list[NewsArticle]:
        sym = symbol.strip().upper()
        with session_scope() as s:
            rows = (
                s.execute(
                    select(NewsRow)
                    .order_by(NewsRow.published_at.desc(), NewsRow.id.desc())
                    .limit(500)
                )
                .scalars()
                .all()
            )
            matches = [self._to_article(r) for r in rows if sym in (r.symbols or [])]
            return matches[:limit]

    @staticmethod
    def _to_article(row: NewsRow) -> NewsArticle:
        return NewsArticle(
            id=row.id,
            source=row.source,
            title=row.title,
            url=row.url,
            summary=row.summary,
            symbols=list(row.symbols or []),
            published_at=row.published_at,
        )
