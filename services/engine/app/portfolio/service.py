"""Portfolio holdings CRUD + pure P&L computation.

CRUD uses the direct-session style (like the watchlists/settings services). The
P&L math lives in module-level pure functions (``position_from`` / ``summarize``)
so it is unit-testable without a database or network.
"""

from __future__ import annotations

from sqlalchemy import select

from app.data.models import Quote
from app.db.models import HoldingRow
from app.db.session import session_scope
from app.portfolio.schemas import (
    Holding,
    HoldingCreate,
    HoldingUpdate,
    PortfolioPosition,
    PortfolioTotal,
)


class PortfolioService:
    def list(self) -> list[Holding]:
        with session_scope() as s:
            rows = (
                s.execute(select(HoldingRow).order_by(HoldingRow.symbol, HoldingRow.id))
                .scalars()
                .all()
            )
            return [self._to_schema(r) for r in rows]

    def add(self, data: HoldingCreate) -> Holding:
        with session_scope() as s:
            row = HoldingRow(
                symbol=data.symbol.strip().upper(),
                quantity=data.quantity,
                avg_cost=data.avg_cost,
                currency=(data.currency or "USD").upper(),
                purchase_date=data.purchase_date,
                target_price=data.target_price,
                stop_loss=data.stop_loss,
                notes=data.notes,
            )
            s.add(row)
            s.flush()
            return self._to_schema(row)

    def update(self, holding_id: int, data: HoldingUpdate) -> Holding | None:
        with session_scope() as s:
            row = s.get(HoldingRow, holding_id)
            if row is None:
                return None
            for field, value in data.model_dump(exclude_unset=True).items():
                if field == "currency" and value:
                    value = value.upper()
                setattr(row, field, value)
            s.flush()
            return self._to_schema(row)

    def delete(self, holding_id: int) -> bool:
        with session_scope() as s:
            row = s.get(HoldingRow, holding_id)
            if row is None:
                return False
            s.delete(row)
            return True

    @staticmethod
    def _to_schema(row: HoldingRow) -> Holding:
        return Holding(
            id=row.id,
            symbol=row.symbol,
            quantity=row.quantity,
            avg_cost=row.avg_cost,
            currency=row.currency,
            purchase_date=row.purchase_date,
            target_price=row.target_price,
            stop_loss=row.stop_loss,
            notes=row.notes,
        )


def position_from(holding: Holding, quote: Quote | None) -> PortfolioPosition:
    """Enrich a holding with its live quote and compute P&L (pure)."""
    price = quote.price if quote else None
    change = quote.change if quote else None
    cost_basis = holding.avg_cost * holding.quantity
    market_value = price * holding.quantity if price is not None else None
    unrealized = market_value - cost_basis if market_value is not None else None
    unrealized_pct = (
        (price / holding.avg_cost - 1.0) * 100.0
        if price is not None and holding.avg_cost
        else None
    )
    day_pnl = change * holding.quantity if change is not None else None
    return PortfolioPosition(
        holding=holding,
        name=quote.name if quote else None,
        exchange=quote.exchange if quote else None,
        price=price,
        change=change,
        change_percent=quote.change_percent if quote else None,
        market_value=market_value,
        cost_basis=cost_basis,
        unrealized_pnl=unrealized,
        unrealized_pnl_pct=unrealized_pct,
        day_pnl=day_pnl,
    )


def summarize(positions: list[PortfolioPosition]) -> list[PortfolioTotal]:
    """Aggregate positions into per-currency totals (sorted by currency)."""
    by_ccy: dict[str, dict[str, float]] = {}
    for p in positions:
        agg = by_ccy.setdefault(
            p.holding.currency, {"mv": 0.0, "cb": 0.0, "pnl": 0.0, "day": 0.0}
        )
        agg["cb"] += p.cost_basis
        if p.market_value is not None:
            agg["mv"] += p.market_value
        if p.unrealized_pnl is not None:
            agg["pnl"] += p.unrealized_pnl
        if p.day_pnl is not None:
            agg["day"] += p.day_pnl

    totals: list[PortfolioTotal] = []
    for ccy, a in sorted(by_ccy.items()):
        pct = (a["pnl"] / a["cb"] * 100.0) if a["cb"] else 0.0
        totals.append(
            PortfolioTotal(
                currency=ccy,
                market_value=a["mv"],
                cost_basis=a["cb"],
                unrealized_pnl=a["pnl"],
                unrealized_pnl_pct=pct,
                day_pnl=a["day"],
            )
        )
    return totals
