"""Global search API routes (Phase 9)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.data.models import SymbolRef
from app.search import FacetKind, GlobalSearchResult, GlobalSearchService

from .deps import get_global_search_service

router = APIRouter(prefix="/api/v1/search", tags=["search"])

SearchDep = Annotated[GlobalSearchService, Depends(get_global_search_service)]


@router.get("/global", response_model=GlobalSearchResult, summary="Global search")
async def global_search(
    service: SearchDep,
    q: Annotated[str, Query(min_length=1, description="Ticker, company, sector, country…")],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> GlobalSearchResult:
    return await service.search(q, limit=limit)


@router.get(
    "/facet/{kind}/{label}",
    response_model=list[SymbolRef],
    summary="Symbols for a search facet",
)
async def facet_symbols(
    service: SearchDep,
    kind: FacetKind,
    label: str,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> list[SymbolRef]:
    return await service.symbols_for_facet(kind, label, limit=limit)
