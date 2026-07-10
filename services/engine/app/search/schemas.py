"""Global search schemas (Phase 9)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from app.data.models import SymbolRef


class FacetKind(StrEnum):
    SECTOR = "sector"
    INDUSTRY = "industry"
    COUNTRY = "country"


class FacetHit(BaseModel):
    kind: FacetKind
    label: str
    count: int
    sample_symbols: list[SymbolRef] = Field(default_factory=list)


class GlobalSearchResult(BaseModel):
    query: str
    symbols: list[SymbolRef] = Field(default_factory=list)
    facets: list[FacetHit] = Field(default_factory=list)
