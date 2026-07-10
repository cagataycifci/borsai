"""Global search service: symbols + sector/industry/country facets (Phase 9)."""

from __future__ import annotations

from app.data.models import SymbolRef
from app.data.service import MarketDataService
from app.data.universe.service import SymbolUniverseService
from app.db.repositories import SymbolRepository
from app.db.session import session_scope
from app.search.schemas import FacetHit, FacetKind, GlobalSearchResult

# Exchange groups exposed as searchable countries/regions.
_COUNTRY_EXCHANGES: dict[str, tuple[str, list[str]]] = {
    "united states": ("United States", ["NYSE", "NASDAQ", "AMEX"]),
    "us": ("United States", ["NYSE", "NASDAQ", "AMEX"]),
    "usa": ("United States", ["NYSE", "NASDAQ", "AMEX"]),
    "america": ("United States", ["NYSE", "NASDAQ", "AMEX"]),
    "turkey": ("Turkey", ["BIST"]),
    "türkiye": ("Turkey", ["BIST"]),
    "turkiye": ("Turkey", ["BIST"]),
    "tr": ("Turkey", ["BIST"]),
    "bist": ("Turkey", ["BIST"]),
}


class GlobalSearchService:
    def __init__(self, universe: SymbolUniverseService, market: MarketDataService) -> None:
        self._universe = universe
        self._market = market

    async def search(self, query: str, limit: int = 20) -> GlobalSearchResult:
        q = query.strip()
        if not q:
            return GlobalSearchResult(query=q)

        symbols = await self._search_symbols(q, limit=limit)
        facets = self._search_facets(q, limit=6)
        return GlobalSearchResult(query=q, symbols=symbols, facets=facets)

    async def symbols_for_facet(
        self, kind: FacetKind, label: str, limit: int = 30
    ) -> list[SymbolRef]:
        with session_scope() as s:
            repo = SymbolRepository(s)
            if kind == FacetKind.SECTOR:
                return repo.symbols_by_sector(label, limit=limit)
            if kind == FacetKind.INDUSTRY:
                return repo.symbols_by_industry(label, limit=limit)
            if kind == FacetKind.COUNTRY:
                exchanges = _country_exchanges(label)
                if exchanges:
                    return repo.symbols_by_exchanges(exchanges, limit=limit)
        return []

    async def _search_symbols(self, query: str, limit: int) -> list[SymbolRef]:
        results = self._universe.search(query, limit=limit)
        if len(results) < 5:
            seen = {r.symbol for r in results}
            for ref in await self._market.search(query):
                if ref.symbol not in seen:
                    seen.add(ref.symbol)
                    results.append(ref)
        return results[:limit]

    def _search_facets(self, query: str, limit: int) -> list[FacetHit]:
        q = query.strip()
        ql = q.lower()
        facets: list[FacetHit] = []

        with session_scope() as s:
            repo = SymbolRepository(s)

            for sector, count in repo.search_sectors(q, limit=limit):
                facets.append(
                    FacetHit(
                        kind=FacetKind.SECTOR,
                        label=sector,
                        count=count,
                        sample_symbols=repo.symbols_by_sector(sector, limit=3),
                    )
                )

            for industry, count in repo.search_industries(q, limit=limit):
                facets.append(
                    FacetHit(
                        kind=FacetKind.INDUSTRY,
                        label=industry,
                        count=count,
                        sample_symbols=repo.symbols_by_industry(industry, limit=3),
                    )
                )

            for label, exchanges in _matching_countries(ql):
                count = repo.count_by_exchanges(exchanges)
                if count:
                    facets.append(
                        FacetHit(
                            kind=FacetKind.COUNTRY,
                            label=label,
                            count=count,
                            sample_symbols=repo.symbols_by_exchanges(exchanges, limit=3),
                        )
                    )

        return facets[:limit]


def _matching_countries(query_lower: str) -> list[tuple[str, list[str]]]:
    out: list[tuple[str, list[str]]] = []
    seen: set[str] = set()
    for key, (label, exchanges) in _COUNTRY_EXCHANGES.items():
        if key in query_lower or query_lower in key:
            if label not in seen:
                seen.add(label)
                out.append((label, exchanges))
    return out


def _country_exchanges(label: str) -> list[str] | None:
    ll = label.strip().lower()
    for key, (name, exchanges) in _COUNTRY_EXCHANGES.items():
        if ll == key or ll == name.lower():
            return exchanges
    return None
