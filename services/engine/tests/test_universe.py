"""Tests for the symbol universe repository (search ranking, upsert, BIST seed)."""

from __future__ import annotations


def _seed(rows):
    from app.db.repositories import SymbolRepository
    from app.db.session import session_scope

    with session_scope() as s:
        SymbolRepository(s).bulk_upsert(rows)


def _row(symbol, name, exchange="NASDAQ", currency="USD"):
    return {
        "symbol": symbol,
        "display_symbol": symbol[:-3] if symbol.endswith(".IS") else symbol,
        "name": name,
        "exchange": exchange,
        "asset_type": "EQUITY",
        "currency": currency,
        "sector": None,
        "industry": None,
        "source": "test",
    }


def test_search_ranks_exact_ticker_first(initialized_db) -> None:
    from app.db.repositories import SymbolRepository
    from app.db.session import session_scope

    _seed(
        [
            _row("MU", "Micron Technology"),
            _row("AMD", "Advanced Micro Devices"),
            _row("MUX", "McEwen Mining"),
            _row("ASELS.IS", "Aselsan", exchange="BIST", currency="TRY"),
        ]
    )
    with session_scope() as s:
        results = SymbolRepository(s).search("MU", limit=10)

    assert results[0].display_symbol == "MU"  # exact match ranked first
    symbols = [r.display_symbol for r in results]
    assert "MUX" in symbols  # prefix match included


def test_search_matches_company_name(initialized_db) -> None:
    from app.db.repositories import SymbolRepository
    from app.db.session import session_scope

    _seed([_row("AMD", "Advanced Micro Devices")])
    with session_scope() as s:
        results = SymbolRepository(s).search("micro", limit=10)
    assert any(r.display_symbol == "AMD" for r in results)


def test_bulk_upsert_is_idempotent(initialized_db) -> None:
    from app.db.repositories import SymbolRepository
    from app.db.session import session_scope

    _seed([_row("AAPL", "Apple Inc.")])
    _seed([_row("AAPL", "Apple Inc. (updated)")])  # same PK
    with session_scope() as s:
        repo = SymbolRepository(s)
        assert repo.count() == 1
        assert repo.get("AAPL").name == "Apple Inc. (updated)"


def test_bist_seed_loads(initialized_db) -> None:
    from app.data.universe.loaders import load_bist_symbols

    rows = load_bist_symbols()
    assert len(rows) > 100
    assert all(r["symbol"].endswith(".IS") for r in rows)
    assert all(r["currency"] == "TRY" for r in rows)
    assert any(r["display_symbol"] == "ASELS" for r in rows)
