"""Portfolio (holdings + live P&L) API routes."""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.data.service import MarketDataService
from app.portfolio import (
    Holding,
    HoldingCreate,
    HoldingUpdate,
    PortfolioService,
    PortfolioSummary,
    position_from,
    summarize,
)

from .deps import get_market_data, get_portfolio_service

router = APIRouter(prefix="/api/v1", tags=["portfolio"])

PortfolioDep = Annotated[PortfolioService, Depends(get_portfolio_service)]
MarketData = Annotated[MarketDataService, Depends(get_market_data)]


@router.get("/portfolio", response_model=PortfolioSummary, summary="Holdings + live P&L")
async def get_portfolio(service: PortfolioDep, market: MarketData) -> PortfolioSummary:
    """Join holdings with current quotes (fetched concurrently) and compute P&L,
    aggregated into per-currency totals."""
    holdings = service.list()
    symbols = list({h.symbol for h in holdings})
    results = await asyncio.gather(
        *(market.get_quote(sym) for sym in symbols), return_exceptions=True
    )
    quotes = {
        sym: (res if not isinstance(res, BaseException) else None)
        for sym, res in zip(symbols, results, strict=True)
    }
    positions = [position_from(h, quotes.get(h.symbol)) for h in holdings]
    return PortfolioSummary(positions=positions, totals=summarize(positions))


@router.get("/holdings", response_model=list[Holding], summary="Raw holdings")
def list_holdings(service: PortfolioDep) -> list[Holding]:
    return service.list()


@router.post("/holdings", response_model=Holding, summary="Add a holding")
def add_holding(service: PortfolioDep, body: HoldingCreate) -> Holding:
    return service.add(body)


@router.put("/holdings/{holding_id}", response_model=Holding, summary="Update a holding")
def update_holding(
    service: PortfolioDep, holding_id: int, body: HoldingUpdate
) -> Holding:
    holding = service.update(holding_id, body)
    if holding is None:
        raise HTTPException(status_code=404, detail=f"No holding {holding_id}")
    return holding


@router.delete("/holdings/{holding_id}", summary="Delete a holding")
def delete_holding(service: PortfolioDep, holding_id: int) -> dict[str, bool]:
    if not service.delete(holding_id):
        raise HTTPException(status_code=404, detail=f"No holding {holding_id}")
    return {"deleted": True}
