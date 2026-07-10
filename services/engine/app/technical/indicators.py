"""Technical indicators.

Pure pandas computations over canonical :class:`app.data.models.Candle` series.
Each public ``calc_*`` function returns one or more named pandas Series aligned
to the candle index; the :func:`compute_indicators` orchestrator parses a compact
spec string (e.g. ``"sma:20,ema:50,rsi,macd,bbands:20:2,vwap"``) and emits
render-ready :class:`IndicatorSeries` with a ``pane`` hint so the renderer knows
whether a line overlays the price scale or needs its own sub-pane.

These indicators are deliberately decoupled from charts so alerts (Phase 7) and
AI analysis (Phase 6) can reuse them.
"""

from __future__ import annotations

import math
from datetime import datetime

import pandas as pd
from pydantic import BaseModel

from app.data.models import Candle

# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class IndicatorPoint(BaseModel):
    time: datetime
    value: float | None  # None during warm-up / undefined regions


class IndicatorSeries(BaseModel):
    name: str  # e.g. "SMA 20", "MACD", "BB Upper"
    key: str  # stable id, e.g. "sma_20", "macd", "bb_upper"
    pane: str  # render hint: "price" | "rsi" | "macd" | "stoch" | "atr"
    style: str = "line"  # "line" | "histogram"
    points: list[IndicatorPoint]


class IndicatorResponse(BaseModel):
    symbol: str
    interval: str
    series: list[IndicatorSeries]


# ---------------------------------------------------------------------------
# Frame helpers
# ---------------------------------------------------------------------------


def candles_to_frame(candles: list[Candle]) -> pd.DataFrame:
    """Build a time-indexed OHLCV DataFrame from candles (sorted ascending)."""
    frame = pd.DataFrame(
        {
            "open": [c.open for c in candles],
            "high": [c.high for c in candles],
            "low": [c.low for c in candles],
            "close": [c.close for c in candles],
            "volume": [c.volume for c in candles],
        },
        index=pd.DatetimeIndex([c.time for c in candles], name="time"),
    ).sort_index()
    return frame


def _points(index: pd.DatetimeIndex, series: pd.Series) -> list[IndicatorPoint]:
    """Convert a pandas Series to indicator points, mapping NaN/inf → None."""
    out: list[IndicatorPoint] = []
    for ts, value in zip(index, series, strict=False):
        v = float(value) if value is not None else None
        if v is not None and not math.isfinite(v):
            v = None
        out.append(IndicatorPoint(time=ts.to_pydatetime(), value=v))
    return out


# ---------------------------------------------------------------------------
# Indicator math
# ---------------------------------------------------------------------------


def calc_sma(close: pd.Series, period: int) -> pd.Series:
    return close.rolling(window=period, min_periods=period).mean()


def calc_ema(close: pd.Series, period: int) -> pd.Series:
    return close.ewm(span=period, adjust=False, min_periods=period).mean()


def calc_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's RSI."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def calc_macd(
    close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> dict[str, pd.Series]:
    macd_line = calc_ema(close, fast) - calc_ema(close, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    return {
        "macd": macd_line,
        "signal": signal_line,
        "histogram": macd_line - signal_line,
    }


def calc_bbands(
    close: pd.Series, period: int = 20, std: float = 2.0
) -> dict[str, pd.Series]:
    middle = close.rolling(window=period, min_periods=period).mean()
    deviation = close.rolling(window=period, min_periods=period).std(ddof=0)
    return {
        "upper": middle + std * deviation,
        "middle": middle,
        "lower": middle - std * deviation,
    }


def calc_vwap(frame: pd.DataFrame) -> pd.Series:
    """Cumulative VWAP over the supplied window (not session-anchored)."""
    typical = (frame["high"] + frame["low"] + frame["close"]) / 3.0
    cum_vol = frame["volume"].cumsum()
    cum_tpv = (typical * frame["volume"]).cumsum()
    return cum_tpv / cum_vol.replace(0.0, math.nan)


def calc_stochastic(
    frame: pd.DataFrame, k_period: int = 14, d_period: int = 3
) -> dict[str, pd.Series]:
    low_k = frame["low"].rolling(window=k_period, min_periods=k_period).min()
    high_k = frame["high"].rolling(window=k_period, min_periods=k_period).max()
    percent_k = 100.0 * (frame["close"] - low_k) / (high_k - low_k)
    percent_d = percent_k.rolling(window=d_period, min_periods=d_period).mean()
    return {"k": percent_k, "d": percent_d}


def calc_atr(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range (Wilder's smoothing)."""
    prev_close = frame["close"].shift(1)
    true_range = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - prev_close).abs(),
            (frame["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def calc_ichimoku(
    frame: pd.DataFrame, tenkan: int = 9, kijun: int = 26, senkou_b: int = 52
) -> dict[str, pd.Series]:
    high, low = frame["high"], frame["low"]

    def midpoint(period: int) -> pd.Series:
        return (
            high.rolling(window=period, min_periods=period).max()
            + low.rolling(window=period, min_periods=period).min()
        ) / 2.0

    tenkan_sen = midpoint(tenkan)
    kijun_sen = midpoint(kijun)
    return {
        "tenkan": tenkan_sen,
        "kijun": kijun_sen,
        # Leading spans are projected forward by `kijun` periods in classic
        # Ichimoku; we keep them index-aligned for simplicity and let the chart
        # offset if desired.
        "senkou_a": (tenkan_sen + kijun_sen) / 2.0,
        "senkou_b": midpoint(senkou_b),
        "chikou": frame["close"].shift(-kijun),
    }


# ---------------------------------------------------------------------------
# Spec parsing + orchestration
# ---------------------------------------------------------------------------


def _parse_spec(spec: str) -> list[tuple[str, list[float]]]:
    """Parse ``"sma:20,ema:50,macd"`` → ``[("sma",[20]), ("ema",[50]), ("macd",[])]``."""
    parsed: list[tuple[str, list[float]]] = []
    for token in spec.split(","):
        token = token.strip().lower()
        if not token:
            continue
        name, *raw = token.split(":")
        params: list[float] = []
        for p in raw:
            try:
                params.append(float(p))
            except ValueError:
                continue
        parsed.append((name, params))
    return parsed


def compute_indicators(
    symbol: str, interval: str, candles: list[Candle], spec: str
) -> IndicatorResponse:
    """Compute the indicators named in ``spec`` for the given candles."""
    series: list[IndicatorSeries] = []
    if not candles:
        return IndicatorResponse(symbol=symbol, interval=interval, series=series)

    frame = candles_to_frame(candles)
    idx = frame.index
    close = frame["close"]

    for name, params in _parse_spec(spec):
        if name == "sma":
            period = int(params[0]) if params else 20
            series.append(
                IndicatorSeries(
                    name=f"SMA {period}",
                    key=f"sma_{period}",
                    pane="price",
                    points=_points(idx, calc_sma(close, period)),
                )
            )
        elif name == "ema":
            period = int(params[0]) if params else 20
            series.append(
                IndicatorSeries(
                    name=f"EMA {period}",
                    key=f"ema_{period}",
                    pane="price",
                    points=_points(idx, calc_ema(close, period)),
                )
            )
        elif name == "vwap":
            series.append(
                IndicatorSeries(
                    name="VWAP",
                    key="vwap",
                    pane="price",
                    points=_points(idx, calc_vwap(frame)),
                )
            )
        elif name in {"bbands", "bb"}:
            period = int(params[0]) if params else 20
            std = params[1] if len(params) > 1 else 2.0
            bands = calc_bbands(close, period, std)
            for label, key in (("Upper", "upper"), ("Middle", "middle"), ("Lower", "lower")):
                series.append(
                    IndicatorSeries(
                        name=f"BB {label}",
                        key=f"bb_{key}",
                        pane="price",
                        points=_points(idx, bands[key]),
                    )
                )
        elif name == "ichimoku":
            cloud = calc_ichimoku(frame)
            for label, key in (
                ("Tenkan", "tenkan"),
                ("Kijun", "kijun"),
                ("Senkou A", "senkou_a"),
                ("Senkou B", "senkou_b"),
                ("Chikou", "chikou"),
            ):
                series.append(
                    IndicatorSeries(
                        name=f"Ichimoku {label}",
                        key=f"ichimoku_{key}",
                        pane="price",
                        points=_points(idx, cloud[key]),
                    )
                )
        elif name == "rsi":
            period = int(params[0]) if params else 14
            series.append(
                IndicatorSeries(
                    name=f"RSI {period}",
                    key=f"rsi_{period}",
                    pane="rsi",
                    points=_points(idx, calc_rsi(close, period)),
                )
            )
        elif name == "macd":
            macd = calc_macd(close)
            series.append(
                IndicatorSeries(
                    name="MACD",
                    key="macd",
                    pane="macd",
                    points=_points(idx, macd["macd"]),
                )
            )
            series.append(
                IndicatorSeries(
                    name="Signal",
                    key="macd_signal",
                    pane="macd",
                    points=_points(idx, macd["signal"]),
                )
            )
            series.append(
                IndicatorSeries(
                    name="Histogram",
                    key="macd_hist",
                    pane="macd",
                    style="histogram",
                    points=_points(idx, macd["histogram"]),
                )
            )
        elif name == "stoch":
            k_period = int(params[0]) if params else 14
            d_period = int(params[1]) if len(params) > 1 else 3
            stoch = calc_stochastic(frame, k_period, d_period)
            series.append(
                IndicatorSeries(
                    name="Stoch %K",
                    key="stoch_k",
                    pane="stoch",
                    points=_points(idx, stoch["k"]),
                )
            )
            series.append(
                IndicatorSeries(
                    name="Stoch %D",
                    key="stoch_d",
                    pane="stoch",
                    points=_points(idx, stoch["d"]),
                )
            )
        elif name == "atr":
            period = int(params[0]) if params else 14
            series.append(
                IndicatorSeries(
                    name=f"ATR {period}",
                    key=f"atr_{period}",
                    pane="atr",
                    points=_points(idx, calc_atr(frame, period)),
                )
            )
        # Unknown names are silently ignored — the renderer only requests known keys.

    return IndicatorResponse(symbol=symbol, interval=interval, series=series)
