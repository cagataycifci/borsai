"""SQLite-backed persistence for the latest quote per symbol (write-through).

Decouples the data service from the DB: the service depends on the small
:class:`QuoteStore` protocol, this module provides the concrete SQLite impl.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.data.models import Quote
from app.db.repositories import QuoteCacheRepository
from app.db.session import session_scope

logger = get_logger(__name__)


class SqliteQuoteStore:
    def upsert(self, quote: Quote) -> None:
        try:
            with session_scope() as s:
                QuoteCacheRepository(s).upsert(quote)
        except Exception as exc:  # noqa: BLE001 - persistence is best-effort
            logger.debug("quote persist failed for %s: %s", quote.symbol, exc)

    def get(self, symbol: str) -> Quote | None:
        try:
            with session_scope() as s:
                return QuoteCacheRepository(s).get(symbol)
        except Exception as exc:  # noqa: BLE001
            logger.debug("quote cache read failed for %s: %s", symbol, exc)
            return None
