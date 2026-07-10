"""Finnhub-backed market data adapter (free tier).

Finnhub's free tier covers US equities with near-real-time quotes (better than
yfinance) but does NOT cover Borsa Istanbul and no longer exposes free candles.
So this adapter:
  - returns quotes/fundamentals/search for US symbols,
  - returns ``None``/empty for BIST (``.IS``) symbols and history,
letting the service fall through to the yfinance adapter.

Requires an API key (entered in Settings, stored encrypted).
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.logging import get_logger
from app.data.base import Interval, Range
from app.data.models import (
    AssetType,
    Candle,
    Exchange,
    Fundamentals,
    Quote,
    SymbolRef,
)

logger = get_logger(__name__)

_BASE = "https://finnhub.io/api/v1"


def _clean(value: Any) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) and f != 0.0 else (f if math.isfinite(f) else None)


def _is_bist(symbol: str) -> bool:
    return symbol.upper().endswith(".IS")


class FinnhubAdapter:
    name = "finnhub"

    def __init__(self, api_key: str) -> None:
        self._key = api_key
        self._client = httpx.AsyncClient(
            base_url=_BASE, timeout=10, headers={"X-Finnhub-Token": api_key}
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _get(self, path: str, **params: Any) -> dict | None:
        try:
            resp = await self._client.get(path, params=params)
            if resp.status_code == 429:
                logger.warning("Finnhub rate limit hit for %s", path)
                return None
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Finnhub %s failed: %s", path, exc)
            return None

    async def get_quote(self, symbol: str) -> Quote | None:
        if _is_bist(symbol):
            return None  # unsupported on free tier → fall through to yfinance
        data = await self._get("/quote", symbol=symbol)
        if not data or _clean(data.get("c")) is None:
            return None
        profile = await self._get("/stock/profile2", symbol=symbol) or {}

        price = _clean(data.get("c"))
        prev_close = _clean(data.get("pc"))
        market_cap = _clean(profile.get("marketCapitalization"))
        if market_cap is not None:
            market_cap *= 1_000_000  # Finnhub reports market cap in millions

        return Quote(
            symbol=symbol,
            display_symbol=symbol,
            name=profile.get("name"),
            exchange=_exchange_from_profile(profile),
            currency=profile.get("currency") or "USD",
            price=price,
            previous_close=prev_close,
            open=_clean(data.get("o")),
            day_high=_clean(data.get("h")),
            day_low=_clean(data.get("l")),
            change=_clean(data.get("d")),
            change_percent=_clean(data.get("dp")),
            market_cap=market_cap,
            sector=profile.get("finnhubIndustry"),
            industry=profile.get("finnhubIndustry"),
            source=self.name,
            as_of=datetime.now(UTC),
        )

    async def search(self, query: str) -> list[SymbolRef]:
        data = await self._get("/search", q=query)
        if not data:
            return []
        results: list[SymbolRef] = []
        for item in data.get("result", [])[:15]:
            sym = item.get("symbol")
            if not sym or "." in sym:  # skip foreign-listed dotted symbols
                continue
            results.append(
                SymbolRef(
                    symbol=sym,
                    display_symbol=item.get("displaySymbol") or sym,
                    name=item.get("description") or sym,
                    exchange=Exchange.OTHER,
                    asset_type=AssetType.EQUITY,
                    currency="USD",
                )
            )
        return results

    async def get_history(self, symbol: str, interval: Interval, range_: Range) -> list[Candle]:
        # Candles are premium-only on Finnhub now; yfinance handles history.
        return []

    async def get_fundamentals(self, symbol: str) -> Fundamentals | None:
        if _is_bist(symbol):
            return None
        data = await self._get("/stock/metric", symbol=symbol, metric="all")
        if not data or "metric" not in data:
            return None
        m = data["metric"]
        return Fundamentals(
            symbol=symbol,
            market_cap=_clean(m.get("marketCapitalization")),
            pe_ratio=_clean(m.get("peTTM")),
            forward_pe=_clean(m.get("peBasicExclExtraTTM")),
            eps=_clean(m.get("epsTTM")),
            dividend_yield=_clean(m.get("dividendYieldIndicatedAnnual")),
            beta=_clean(m.get("beta")),
            profit_margin=_clean(m.get("netProfitMarginTTM")),
            revenue=_clean(m.get("revenuePerShareTTM")),
        )


def _exchange_from_profile(profile: dict) -> Exchange:
    exch = (profile.get("exchange") or "").upper()
    if "NASDAQ" in exch:
        return Exchange.NASDAQ
    if "NEW YORK" in exch or "NYSE" in exch:
        return Exchange.NYSE
    if "AMEX" in exch or "AMERICAN" in exch:
        return Exchange.AMEX
    return Exchange.OTHER
