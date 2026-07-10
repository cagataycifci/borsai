"""Symbol universe loaders.

- **US**: the official, free NASDAQ Trader symbol directory files
  (``nasdaqlisted.txt`` + ``otherlisted.txt``), covering NASDAQ, NYSE and AMEX.
- **BIST**: live listing from KAP (``/tr/api/company/items/IGS/A``) with a
  bundled seed (``bist_seed.json``) as offline fallback.

Each loader returns plain dicts ready for :meth:`SymbolRepository.bulk_upsert`.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)

NASDAQ_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
KAP_BIST_COMPANIES_URL = "https://www.kap.org.tr/tr/api/company/items/IGS/A"

_SEED_PATH = Path(__file__).with_name("bist_seed.json")

# otherlisted.txt "Exchange" column → our exchange label.
_OTHER_EXCHANGE_MAP = {
    "A": "AMEX",  # NYSE American
    "N": "NYSE",
    "P": "NYSE",  # NYSE Arca
    "Z": "OTHER",  # Cboe BZX
    "V": "OTHER",  # IEX
}


def _row(symbol: str, name: str, exchange: str, *, currency: str, etf: bool,
         source: str, sector: str | None = None) -> dict:
    return {
        "symbol": symbol,
        "display_symbol": symbol[:-3] if symbol.endswith(".IS") else symbol,
        "name": name.strip(),
        "exchange": exchange,
        "asset_type": "ETF" if etf else "EQUITY",
        "currency": currency,
        "sector": sector,
        "industry": None,
        "source": source,
    }


def _parse_pipe_table(text: str) -> list[list[str]]:
    """Parse a NASDAQ Trader pipe-delimited file (skips header + footer)."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    rows: list[list[str]] = []
    for ln in lines[1:]:  # skip header
        if ln.startswith("File Creation Time"):
            break
        rows.append(ln.split("|"))
    return rows


async def load_us_symbols(client: httpx.AsyncClient) -> list[dict]:
    out: list[dict] = []

    # nasdaqlisted cols: Symbol|Name|MktCat|TestIssue|FinStatus|RoundLot|ETF|NextShares
    try:
        resp = await client.get(NASDAQ_LISTED_URL, timeout=30)
        resp.raise_for_status()
        for cols in _parse_pipe_table(resp.text):
            if len(cols) < 7 or cols[3] == "Y":  # skip test issues
                continue
            symbol = cols[0].strip()
            if not symbol or "$" in symbol:
                continue
            out.append(_row(symbol, cols[1], "NASDAQ", currency="USD",
                            etf=cols[6] == "Y", source="nasdaqtrader"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to load nasdaqlisted.txt: %s", exc)

    # otherlisted cols: ACTSymbol|Name|Exchange|CQSSymbol|ETF|RoundLot|TestIssue|NasdaqSym
    try:
        resp = await client.get(OTHER_LISTED_URL, timeout=30)
        resp.raise_for_status()
        for cols in _parse_pipe_table(resp.text):
            if len(cols) < 8 or cols[6] == "Y":  # skip test issues
                continue
            symbol = cols[0].strip()
            if not symbol or "$" in symbol:
                continue
            exchange = _OTHER_EXCHANGE_MAP.get(cols[2].strip(), "OTHER")
            out.append(_row(symbol, cols[1], exchange, currency="USD",
                            etf=cols[4] == "Y", source="nasdaqtrader"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to load otherlisted.txt: %s", exc)

    logger.info("Loaded %d US symbols", len(out))
    return out


async def load_bist_full(client: httpx.AsyncClient) -> list[dict]:
    """Fetch the active BIST equity list from KAP (IGS member type).

    Filters to companies with an active stock code and trading status
    (``payIslemDurumu == "1"``). Returns an empty list on failure so callers
    can fall back to :func:`load_bist_symbols`.
    """
    try:
        resp = await client.get(KAP_BIST_COMPANIES_URL, timeout=30)
        resp.raise_for_status()
        companies = resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to load BIST list from KAP: %s", exc)
        return []

    if not isinstance(companies, list):
        logger.warning("Unexpected KAP response type: %s", type(companies).__name__)
        return []

    out: list[dict] = []
    seen: set[str] = set()
    for item in companies:
        if not isinstance(item, dict):
            continue
        ticker = (item.get("stockCode") or "").strip().upper()
        if not ticker or ticker in seen:
            continue
        # payIslemDurumu: "1" = actively traded on BIST.
        if str(item.get("payIslemDurumu", "")) != "1":
            continue
        seen.add(ticker)
        name = (item.get("kapMemberTitle") or ticker).strip()
        out.append(
            _row(
                f"{ticker}.IS",
                name,
                "BIST",
                currency="TRY",
                etf=False,
                source="kap",
            )
        )

    logger.info("Loaded %d BIST symbols (KAP)", len(out))
    return out


def load_bist_symbols() -> list[dict]:
    try:
        seed = json.loads(_SEED_PATH.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to load BIST seed: %s", exc)
        return []
    out = [
        _row(f"{e['t']}.IS", e["n"], "BIST", currency="TRY", etf=False,
             source="bist_seed", sector=e.get("s"))
        for e in seed
    ]
    logger.info("Loaded %d BIST symbols (seed)", len(out))
    return out
