"""Search package (Phase 9)."""

from app.search.schemas import FacetHit, FacetKind, GlobalSearchResult
from app.search.service import GlobalSearchService

__all__ = ["FacetHit", "FacetKind", "GlobalSearchResult", "GlobalSearchService"]
