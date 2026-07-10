"""Data-access repositories (sync SQLAlchemy).

Repositories encapsulate all query logic so services depend on intent
(``search_symbols``) rather than ORM/SQL details.
"""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.data.models import Quote, SymbolRef
from app.db.base import utcnow
from app.db.models import QuoteCacheRow, SymbolRow


class SymbolRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def count(self) -> int:
        return self._s.execute(select(func.count()).select_from(SymbolRow)).scalar_one()

    def count_by_exchange(self) -> dict[str, int]:
        rows = self._s.execute(
            select(SymbolRow.exchange, func.count()).group_by(SymbolRow.exchange)
        ).all()
        return {exchange: n for exchange, n in rows}

    def search(self, query: str, limit: int = 20, exchange: str | None = None) -> list[SymbolRef]:
        q = query.strip().upper()
        if not q:
            return []
        like = f"{q}%"
        contains = f"%{q}%"
        stmt = select(SymbolRow).where(
            or_(
                SymbolRow.display_symbol.like(like),
                SymbolRow.symbol.like(like),
                func.upper(SymbolRow.name).like(contains),
            )
        )
        if exchange:
            stmt = stmt.where(SymbolRow.exchange == exchange.upper())
        # Rank exact/prefix ticker matches above name matches.
        stmt = stmt.order_by(
            (SymbolRow.display_symbol == q).desc(),
            SymbolRow.display_symbol.like(like).desc(),
            func.length(SymbolRow.display_symbol),
            SymbolRow.display_symbol,
        ).limit(limit)
        return [self._to_ref(r) for r in self._s.execute(stmt).scalars()]

    def search_sectors(self, query: str, limit: int = 10) -> list[tuple[str, int]]:
        q = f"%{query.strip()}%"
        rows = self._s.execute(
            select(SymbolRow.sector, func.count())
            .where(SymbolRow.sector.is_not(None), SymbolRow.sector.like(q))
            .group_by(SymbolRow.sector)
            .order_by(func.count().desc())
            .limit(limit)
        ).all()
        return [(sector, count) for sector, count in rows if sector]

    def search_industries(self, query: str, limit: int = 10) -> list[tuple[str, int]]:
        q = f"%{query.strip()}%"
        rows = self._s.execute(
            select(SymbolRow.industry, func.count())
            .where(SymbolRow.industry.is_not(None), SymbolRow.industry.like(q))
            .group_by(SymbolRow.industry)
            .order_by(func.count().desc())
            .limit(limit)
        ).all()
        return [(industry, count) for industry, count in rows if industry]

    def symbols_by_sector(self, sector: str, limit: int = 30) -> list[SymbolRef]:
        rows = (
            self._s.execute(
                select(SymbolRow)
                .where(SymbolRow.sector == sector)
                .order_by(SymbolRow.display_symbol)
                .limit(limit)
            )
            .scalars()
            .all()
        )
        return [self._to_ref(r) for r in rows]

    def symbols_by_industry(self, industry: str, limit: int = 30) -> list[SymbolRef]:
        rows = (
            self._s.execute(
                select(SymbolRow)
                .where(SymbolRow.industry == industry)
                .order_by(SymbolRow.display_symbol)
                .limit(limit)
            )
            .scalars()
            .all()
        )
        return [self._to_ref(r) for r in rows]

    def symbols_by_exchanges(self, exchanges: list[str], limit: int = 30) -> list[SymbolRef]:
        rows = (
            self._s.execute(
                select(SymbolRow)
                .where(SymbolRow.exchange.in_(exchanges))
                .order_by(SymbolRow.display_symbol)
                .limit(limit)
            )
            .scalars()
            .all()
        )
        return [self._to_ref(r) for r in rows]

    def count_by_exchanges(self, exchanges: list[str]) -> int:
        return self._s.execute(
            select(func.count())
            .select_from(SymbolRow)
            .where(SymbolRow.exchange.in_(exchanges))
        ).scalar_one()

    def get(self, symbol: str) -> SymbolRef | None:
        row = self._s.get(SymbolRow, symbol.upper())
        return self._to_ref(row) if row else None

    def bulk_upsert(self, refs: list[dict]) -> int:
        """Insert-or-update symbols by primary key. Returns rows processed."""
        if not refs:
            return 0
        now = utcnow()
        for r in refs:
            r.setdefault("updated_at", now)
        stmt = sqlite_insert(SymbolRow).values(refs)
        update_cols = {
            c.name: getattr(stmt.excluded, c.name)
            for c in SymbolRow.__table__.columns
            if c.name != "symbol"
        }
        stmt = stmt.on_conflict_do_update(index_elements=["symbol"], set_=update_cols)
        self._s.execute(stmt)
        return len(refs)

    @staticmethod
    def _to_ref(row: SymbolRow) -> SymbolRef:
        return SymbolRef(
            symbol=row.symbol,
            display_symbol=row.display_symbol,
            name=row.name,
            exchange=row.exchange,  # type: ignore[arg-type]
            asset_type=row.asset_type,  # type: ignore[arg-type]
            currency=row.currency,
        )


class QuoteCacheRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def upsert(self, quote: Quote) -> None:
        payload = quote.model_dump(mode="json")
        stmt = sqlite_insert(QuoteCacheRow).values(
            symbol=quote.symbol, payload=payload, fetched_at=utcnow()
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol"],
            set_={"payload": stmt.excluded.payload, "fetched_at": stmt.excluded.fetched_at},
        )
        self._s.execute(stmt)

    def get(self, symbol: str) -> Quote | None:
        row = self._s.get(QuoteCacheRow, symbol.upper())
        if row is None:
            return None
        return Quote.model_validate(row.payload)
