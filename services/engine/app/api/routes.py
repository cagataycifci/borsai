"""REST API routes (v1)."""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.data.base import Interval, Range
from app.data.models import Candle, Fundamentals, Quote, SymbolRef
from app.data.service import MarketDataService
from app.data.universe.service import SymbolUniverseService
from app.technical import (
    IndicatorResponse,
    VolumeProfileResponse,
    compute_indicators,
    compute_volume_profile,
)

from .deps import get_market_data, get_symbol_universe

router = APIRouter(prefix="/api/v1")

MarketData = Annotated[MarketDataService, Depends(get_market_data)]
Universe = Annotated[SymbolUniverseService, Depends(get_symbol_universe)]


@router.get("/search", response_model=list[SymbolRef], summary="Search symbols")
async def search_symbols(
    market: MarketData,
    universe: Universe,
    q: Annotated[str, Query(min_length=1, description="Ticker or company name")],
    limit: int = 20,
) -> list[SymbolRef]:
    """Search the local symbol universe first (fast, offline); if it yields too
    few results, fall back to the live provider search and merge (deduped)."""
    results = universe.search(q, limit=limit)
    if len(results) < 5:
        seen = {r.symbol for r in results}
        for ref in await market.search(q):
            if ref.symbol not in seen:
                seen.add(ref.symbol)
                results.append(ref)
    return results[:limit]


@router.get("/quote/{symbol}", response_model=Quote, summary="Latest quote snapshot")
async def get_quote(service: MarketData, symbol: str) -> Quote:
    quote = await service.get_quote(symbol)
    if quote is None:
        raise HTTPException(status_code=404, detail=f"No quote for '{symbol}'")
    return quote


@router.get(
    "/history/{symbol}",
    response_model=list[Candle],
    summary="Historical OHLCV candles",
)
async def get_history(
    service: MarketData,
    symbol: str,
    interval: Interval = Interval.D1,
    range_: Annotated[Range, Query(alias="range")] = Range.Y1,
) -> list[Candle]:
    return await service.get_history(symbol, interval, range_)


@router.get(
    "/indicators/{symbol}",
    response_model=IndicatorResponse,
    summary="Technical indicators over historical candles",
)
async def get_indicators(
    service: MarketData,
    symbol: str,
    indicators: Annotated[
        str,
        Query(
            description="Comma list, e.g. 'sma:20,ema:50,rsi,macd,bbands:20:2,vwap'"
        ),
    ] = "sma:20,ema:50",
    interval: Interval = Interval.D1,
    range_: Annotated[Range, Query(alias="range")] = Range.Y1,
) -> IndicatorResponse:
    """Compute indicators over the same candle series the chart renders, so lines
    align exactly. Computation is offloaded to a thread (pandas is blocking)."""
    candles = await service.get_history(symbol, interval, range_)
    return await asyncio.to_thread(
        compute_indicators, service.normalize(symbol), interval.value, candles, indicators
    )


@router.get(
    "/volume-profile/{symbol}",
    response_model=VolumeProfileResponse,
    summary="Volume-by-price profile over historical candles",
)
async def get_volume_profile(
    service: MarketData,
    symbol: str,
    bins: Annotated[int, Query(ge=1, le=200, description="Number of price levels")] = 24,
    interval: Interval = Interval.D1,
    range_: Annotated[Range, Query(alias="range")] = Range.Y1,
) -> VolumeProfileResponse:
    """Compute the volume profile over the same candles the chart renders so the
    levels line up with the price axis. Offloaded to a thread (CPU-bound)."""
    candles = await service.get_history(symbol, interval, range_)
    return await asyncio.to_thread(
        compute_volume_profile, service.normalize(symbol), interval.value, candles, bins
    )


@router.get(
    "/fundamentals/{symbol}",
    response_model=Fundamentals,
    summary="Fundamental snapshot",
)
async def get_fundamentals(service: MarketData, symbol: str) -> Fundamentals:
    fundamentals = await service.get_fundamentals(symbol)
    if fundamentals is None:
        raise HTTPException(status_code=404, detail=f"No fundamentals for '{symbol}'")
    return fundamentals
