"""Symbol universe service: load/refresh the symbol DB and serve fast local search."""

from __future__ import annotations

import httpx

from app.core.logging import get_logger
from app.data.models import SymbolRef
from app.db.repositories import SymbolRepository
from app.db.session import session_scope

from .loaders import load_bist_full, load_bist_symbols, load_us_symbols

logger = get_logger(__name__)

_UPSERT_BATCH = 500


class SymbolUniverseService:
    async def refresh(self) -> dict[str, int]:
        """Fetch US (live) + BIST (KAP, seed fallback) symbols and upsert them."""
        async with httpx.AsyncClient(headers={"User-Agent": "BorsaAI/0.1"}) as client:
            us = await load_us_symbols(client)
            bist = await load_bist_full(client)
        if not bist:
            bist = load_bist_symbols()
        all_rows = us + bist

        processed = 0
        with session_scope() as s:
            repo = SymbolRepository(s)
            for i in range(0, len(all_rows), _UPSERT_BATCH):
                processed += repo.bulk_upsert(all_rows[i : i + _UPSERT_BATCH])

        stats = self.stats()
        logger.info("Universe refreshed: %s", stats)
        return stats

    async def ensure_seeded(self) -> None:
        """Populate the universe on first run (empty DB) without blocking startup
        on network failures."""
        if self.count() > 0:
            return
        try:
            await self.refresh()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Initial universe seed failed (will retry on demand): %s", exc)
            # Ensure at least BIST seed is present even if the US fetch failed.
            bist = load_bist_symbols()
            if bist:
                with session_scope() as s:
                    SymbolRepository(s).bulk_upsert(bist)

    def search(self, query: str, limit: int = 20, exchange: str | None = None) -> list[SymbolRef]:
        with session_scope() as s:
            return SymbolRepository(s).search(query, limit=limit, exchange=exchange)

    def get(self, symbol: str) -> SymbolRef | None:
        with session_scope() as s:
            return SymbolRepository(s).get(symbol)

    def count(self) -> int:
        with session_scope() as s:
            return SymbolRepository(s).count()

    def stats(self) -> dict[str, int]:
        with session_scope() as s:
            repo = SymbolRepository(s)
            by_exchange = repo.count_by_exchange()
            return {"total": repo.count(), **by_exchange}
