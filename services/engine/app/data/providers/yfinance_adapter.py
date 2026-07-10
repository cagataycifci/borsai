"""yfinance-backed market data adapter (free tier).

yfinance is synchronous and pandas-based; every blocking call is offloaded to a
thread via ``asyncio.to_thread`` so it never stalls the event loop. Data is
delayed (typically ~15 min) — acceptable for the free tier and clearly labelled
in the UI. Treat every call as best-effort: providers fail, and we degrade
gracefully rather than raise.
"""

from __future__ import annotations

import asyncio
import math
from datetime import UTC, datetime
from typing import Any

import yfinance as yf

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

# yfinance exchange codes → our Exchange enum.
_EXCHANGE_MAP: dict[str, Exchange] = {
    "NMS": Exchange.NASDAQ,
    "NGM": Exchange.NASDAQ,
    "NCM": Exchange.NASDAQ,
    "NYQ": Exchange.NYSE,
    "PCX": Exchange.NYSE,
    "ASE": Exchange.AMEX,
    "AMX": Exchange.AMEX,
    "IST": Exchange.BIST,
}

_INTERVAL_MAP: dict[Interval, str] = {
    Interval.M1: "1m",
    Interval.M5: "5m",
    Interval.M15: "15m",
    Interval.M30: "30m",
    Interval.H1: "60m",
    Interval.H4: "60m",  # yfinance has no 4h; service resamples 1h→4h (technical.resample)
    Interval.D1: "1d",
    Interval.W1: "1wk",
    Interval.MO1: "1mo",
}


def _clean(value: Any) -> float | None:
    """Coerce a value to a finite float or None (handles NaN/inf/None)."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _display_symbol(symbol: str) -> str:
    return symbol[:-3] if symbol.upper().endswith(".IS") else symbol


def _exchange_for(symbol: str, code: str | None) -> Exchange:
    if symbol.upper().endswith(".IS"):
        return Exchange.BIST
    return _EXCHANGE_MAP.get(code or "", Exchange.OTHER)


class YFinanceAdapter:
    name = "yfinance"

    async def get_quote(self, symbol: str) -> Quote | None:
        return await asyncio.to_thread(self._get_quote_sync, symbol)

    def _get_quote_sync(self, symbol: str) -> Quote | None:
        try:
            ticker = yf.Ticker(symbol)
            fast = ticker.fast_info
            # fast_info is reliable for prices; .info is richer but slower/flaky.
            info: dict[str, Any] = {}
            try:
                info = ticker.info or {}
            except Exception:  # noqa: BLE001 - .info is notoriously fragile
                info = {}

            price = _clean(getattr(fast, "last_price", None)) or _clean(
                info.get("currentPrice")
            )
            prev_close = _clean(getattr(fast, "previous_close", None)) or _clean(
                info.get("previousClose")
            )
            if price is None and prev_close is None:
                return None

            change = None
            change_pct = None
            if price is not None and prev_close:
                change = price - prev_close
                change_pct = (change / prev_close) * 100 if prev_close else None

            currency = (
                getattr(fast, "currency", None) or info.get("currency") or "USD"
            )
            exchange = _exchange_for(symbol, info.get("exchange"))

            return Quote(
                symbol=symbol,
                display_symbol=_display_symbol(symbol),
                name=info.get("shortName") or info.get("longName"),
                exchange=exchange,
                currency=currency,
                price=price,
                previous_close=prev_close,
                open=_clean(getattr(fast, "open", None)) or _clean(info.get("open")),
                day_high=_clean(getattr(fast, "day_high", None))
                or _clean(info.get("dayHigh")),
                day_low=_clean(getattr(fast, "day_low", None))
                or _clean(info.get("dayLow")),
                change=change,
                change_percent=change_pct,
                volume=_clean(getattr(fast, "last_volume", None))
                or _clean(info.get("volume")),
                market_cap=_clean(getattr(fast, "market_cap", None))
                or _clean(info.get("marketCap")),
                pe_ratio=_clean(info.get("trailingPE")),
                eps=_clean(info.get("trailingEps")),
                dividend_yield=_clean(info.get("dividendYield")),
                week52_high=_clean(getattr(fast, "year_high", None))
                or _clean(info.get("fiftyTwoWeekHigh")),
                week52_low=_clean(getattr(fast, "year_low", None))
                or _clean(info.get("fiftyTwoWeekLow")),
                sector=info.get("sector"),
                industry=info.get("industry"),
                source=self.name,
                as_of=datetime.now(UTC),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("yfinance get_quote(%s) failed: %s", symbol, exc)
            return None

    async def search(self, query: str) -> list[SymbolRef]:
        return await asyncio.to_thread(self._search_sync, query)

    def _search_sync(self, query: str) -> list[SymbolRef]:
        try:
            search = yf.Search(query, max_results=15)
            quotes = getattr(search, "quotes", []) or []
        except Exception as exc:  # noqa: BLE001
            logger.warning("yfinance search(%s) failed: %s", query, exc)
            quotes = []

        results: list[SymbolRef] = []
        for q in quotes:
            sym = q.get("symbol")
            if not sym:
                continue
            code = q.get("exchange")
            qtype = (q.get("quoteType") or "").upper()
            results.append(
                SymbolRef(
                    symbol=sym,
                    display_symbol=_display_symbol(sym),
                    name=q.get("shortname") or q.get("longname") or sym,
                    exchange=_exchange_for(sym, code),
                    asset_type=_asset_type(qtype),
                    currency="TRY" if sym.upper().endswith(".IS") else "USD",
                )
            )
        return results

    async def get_history(
        self, symbol: str, interval: Interval, range_: Range
    ) -> list[Candle]:
        return await asyncio.to_thread(self._get_history_sync, symbol, interval, range_)

    def _get_history_sync(
        self, symbol: str, interval: Interval, range_: Range
    ) -> list[Candle]:
        try:
            df = yf.Ticker(symbol).history(
                period=range_.value, interval=_INTERVAL_MAP[interval], auto_adjust=False
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("yfinance history(%s) failed: %s", symbol, exc)
            return []

        candles: list[Candle] = []
        for idx, row in df.iterrows():
            ts = idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx
            candles.append(
                Candle(
                    time=ts,
                    open=_clean(row.get("Open")) or 0.0,
                    high=_clean(row.get("High")) or 0.0,
                    low=_clean(row.get("Low")) or 0.0,
                    close=_clean(row.get("Close")) or 0.0,
                    volume=_clean(row.get("Volume")) or 0.0,
                )
            )
        return candles

    async def get_fundamentals(self, symbol: str) -> Fundamentals | None:
        return await asyncio.to_thread(self._get_fundamentals_sync, symbol)

    def _get_fundamentals_sync(self, symbol: str) -> Fundamentals | None:
        try:
            info = yf.Ticker(symbol).info or {}
        except Exception as exc:  # noqa: BLE001
            logger.warning("yfinance fundamentals(%s) failed: %s", symbol, exc)
            return None
        if not info:
            return None
        return Fundamentals(
            symbol=symbol,
            market_cap=_clean(info.get("marketCap")),
            pe_ratio=_clean(info.get("trailingPE")),
            forward_pe=_clean(info.get("forwardPE")),
            eps=_clean(info.get("trailingEps")),
            dividend_yield=_clean(info.get("dividendYield")),
            beta=_clean(info.get("beta")),
            profit_margin=_clean(info.get("profitMargins")),
            revenue=_clean(info.get("totalRevenue")),
            sector=info.get("sector"),
            industry=info.get("industry"),
        )


def _asset_type(quote_type: str) -> AssetType:
    return {
        "EQUITY": AssetType.EQUITY,
        "ETF": AssetType.ETF,
        "INDEX": AssetType.INDEX,
        "CRYPTOCURRENCY": AssetType.CRYPTO,
    }.get(quote_type, AssetType.OTHER)
