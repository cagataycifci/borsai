"""Symbol universe routes: stats and refresh."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.data.universe.service import SymbolUniverseService

from .deps import get_symbol_universe

router = APIRouter(prefix="/api/v1/symbols")

Universe = Annotated[SymbolUniverseService, Depends(get_symbol_universe)]


@router.get("/stats", summary="Universe size by exchange")
def universe_stats(universe: Universe) -> dict[str, int]:
    return universe.stats()


@router.post("/refresh", summary="Reload the symbol universe (US live + BIST KAP)")
async def refresh_universe(universe: Universe) -> dict[str, int]:
    return await universe.refresh()
