"""Watchlist CRUD service (sync SQLAlchemy via ``session_scope``).

Mirrors the direct-session style of :class:`app.settings.service.SettingsService`.
Symbols are normalized to upper-case so they line up with quote lookups.
"""

from __future__ import annotations

from sqlalchemy import func, select

from app.db.models import WatchlistItemRow, WatchlistRow
from app.db.session import session_scope
from app.watchlists.schemas import Watchlist

DEFAULT_NAME = "My Watchlist"
DEFAULT_SYMBOLS = ["AAPL", "MSFT", "NVDA", "TSLA", "ASELS.IS", "THYAO.IS", "GARAN.IS"]


class WatchlistService:
    def list(self) -> list[Watchlist]:
        with session_scope() as s:
            rows = (
                s.execute(
                    select(WatchlistRow).order_by(WatchlistRow.position, WatchlistRow.id)
                )
                .scalars()
                .all()
            )
            return [self._to_schema(r) for r in rows]

    def create(self, name: str) -> Watchlist:
        with session_scope() as s:
            max_pos = s.execute(select(func.max(WatchlistRow.position))).scalar()
            row = WatchlistRow(name=name.strip(), position=(max_pos or 0) + 1)
            s.add(row)
            s.flush()
            return self._to_schema(row)

    def rename(self, watchlist_id: int, name: str) -> Watchlist | None:
        with session_scope() as s:
            row = s.get(WatchlistRow, watchlist_id)
            if row is None:
                return None
            row.name = name.strip()
            s.flush()
            return self._to_schema(row)

    def delete(self, watchlist_id: int) -> bool:
        with session_scope() as s:
            row = s.get(WatchlistRow, watchlist_id)
            if row is None:
                return False
            s.delete(row)  # cascades to items (ORM + FK ON DELETE CASCADE)
            return True

    def add_item(self, watchlist_id: int, symbol: str) -> Watchlist | None:
        sym = symbol.strip().upper()
        with session_scope() as s:
            row = s.get(WatchlistRow, watchlist_id)
            if row is None:
                return None
            if sym and sym not in {i.symbol for i in row.items}:
                next_pos = max((i.position for i in row.items), default=-1) + 1
                row.items.append(WatchlistItemRow(symbol=sym, position=next_pos))
                s.flush()
            return self._to_schema(row)

    def remove_item(self, watchlist_id: int, symbol: str) -> Watchlist | None:
        sym = symbol.strip().upper()
        with session_scope() as s:
            row = s.get(WatchlistRow, watchlist_id)
            if row is None:
                return None
            for item in list(row.items):
                if item.symbol == sym:
                    row.items.remove(item)  # delete-orphan removes it on flush
            s.flush()
            return self._to_schema(row)

    def reorder_items(self, watchlist_id: int, symbols: list[str]) -> Watchlist | None:
        order = {sym.strip().upper(): i for i, sym in enumerate(symbols)}
        with session_scope() as s:
            row = s.get(WatchlistRow, watchlist_id)
            if row is None:
                return None
            for item in row.items:
                if item.symbol in order:
                    item.position = order[item.symbol]
            s.flush()
            return self._to_schema(row)

    def ensure_default(self) -> None:
        """Seed a starter watchlist on first run so the UI is never empty."""
        with session_scope() as s:
            count = s.execute(select(func.count()).select_from(WatchlistRow)).scalar_one()
            if count:
                return
            row = WatchlistRow(name=DEFAULT_NAME, position=0)
            row.items = [
                WatchlistItemRow(symbol=sym, position=i)
                for i, sym in enumerate(DEFAULT_SYMBOLS)
            ]
            s.add(row)

    @staticmethod
    def _to_schema(row: WatchlistRow) -> Watchlist:
        symbols = [i.symbol for i in sorted(row.items, key=lambda x: x.position)]
        return Watchlist(id=row.id, name=row.name, position=row.position, symbols=symbols)
