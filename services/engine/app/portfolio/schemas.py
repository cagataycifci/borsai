"""Request/response schemas for the portfolio API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class HoldingBase(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    quantity: float
    avg_cost: float = Field(description="Average cost per share, in `currency`")
    currency: str = "USD"
    purchase_date: datetime | None = None
    target_price: float | None = None
    stop_loss: float | None = None
    notes: str | None = Field(default=None, max_length=512)


class HoldingCreate(HoldingBase):
    pass


class HoldingUpdate(BaseModel):
    """Partial update — only supplied fields change (symbol is immutable)."""

    quantity: float | None = None
    avg_cost: float | None = None
    currency: str | None = None
    purchase_date: datetime | None = None
    target_price: float | None = None
    stop_loss: float | None = None
    notes: str | None = Field(default=None, max_length=512)


class Holding(HoldingBase):
    id: int


class PortfolioPosition(BaseModel):
    """A holding enriched with the live quote and computed P&L."""

    holding: Holding
    name: str | None
    exchange: str | None
    price: float | None
    change: float | None
    change_percent: float | None
    market_value: float | None
    cost_basis: float
    unrealized_pnl: float | None
    unrealized_pnl_pct: float | None
    day_pnl: float | None


class PortfolioTotal(BaseModel):
    """Aggregate per currency (no cross-currency conversion — no FX feed)."""

    currency: str
    market_value: float
    cost_basis: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    day_pnl: float


class PortfolioSummary(BaseModel):
    positions: list[PortfolioPosition]
    totals: list[PortfolioTotal]
