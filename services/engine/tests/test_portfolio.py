"""Unit tests for portfolio P&L math (pure, no DB/network)."""

from __future__ import annotations

from app.data.models import Quote
from app.portfolio import Holding, position_from, summarize


def _holding(symbol: str, qty: float, cost: float, ccy: str = "USD", hid: int = 1) -> Holding:
    return Holding(id=hid, symbol=symbol, quantity=qty, avg_cost=cost, currency=ccy)


def _quote(symbol: str, price: float, change: float | None = None, ccy: str = "USD") -> Quote:
    return Quote(
        symbol=symbol, display_symbol=symbol, currency=ccy, price=price, change=change
    )


def test_position_pnl_basic() -> None:
    p = position_from(_holding("AAPL", 10, 100.0), _quote("AAPL", 150.0, change=5.0))
    assert p.cost_basis == 1000.0
    assert p.market_value == 1500.0
    assert p.unrealized_pnl == 500.0
    assert p.unrealized_pnl_pct == 50.0
    assert p.day_pnl == 50.0


def test_position_without_quote_is_safe() -> None:
    p = position_from(_holding("AAPL", 10, 100.0), None)
    assert p.cost_basis == 1000.0
    assert p.market_value is None
    assert p.unrealized_pnl is None
    assert p.unrealized_pnl_pct is None
    assert p.price is None
    assert p.day_pnl is None


def test_summarize_groups_by_currency() -> None:
    positions = [
        position_from(_holding("AAPL", 10, 100.0, "USD", 1), _quote("AAPL", 150.0)),
        position_from(_holding("MSFT", 5, 200.0, "USD", 2), _quote("MSFT", 220.0)),
        position_from(
            _holding("ASELS.IS", 100, 50.0, "TRY", 3), _quote("ASELS.IS", 60.0, ccy="TRY")
        ),
    ]
    totals = {t.currency: t for t in summarize(positions)}
    assert set(totals) == {"TRY", "USD"}

    usd = totals["USD"]
    assert usd.cost_basis == 2000.0
    assert usd.market_value == 2600.0
    assert usd.unrealized_pnl == 600.0
    assert round(usd.unrealized_pnl_pct, 2) == 30.0

    assert totals["TRY"].unrealized_pnl == 1000.0


def test_summarize_skips_missing_market_values() -> None:
    # A position with no quote contributes cost basis but not market value.
    positions = [
        position_from(_holding("AAPL", 10, 100.0), _quote("AAPL", 150.0)),
        position_from(_holding("ZZZZ", 10, 100.0), None),
    ]
    (usd,) = summarize(positions)
    assert usd.cost_basis == 2000.0
    assert usd.market_value == 1500.0  # only the quoted position
