"""Pure alert-condition evaluation (Phase 7).

Deliberately free of DB/network: :func:`evaluate` takes an :class:`Alert` plus a
:class:`Snapshot` of already-computed values and returns a human-readable trigger
message (or ``None``). This keeps every condition — including the cross detectors
that need the last two indicator values — trivially unit-testable.

:func:`build_indicators` derives the :class:`Indicators` scalars from a candle
series using :mod:`app.technical` (deterministic, but not needed by the pure tests).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.alerts.schemas import Alert, AlertType
from app.data.models import Candle
from app.technical.indicators import calc_macd, calc_rsi, calc_sma, candles_to_frame


@dataclass
class Indicators:
    """Latest (and previous, for crosses) indicator values."""

    rsi: float | None = None
    macd: float | None = None
    macd_prev: float | None = None
    signal: float | None = None
    signal_prev: float | None = None
    sma_fast: float | None = None
    sma_fast_prev: float | None = None
    sma_slow: float | None = None
    sma_slow_prev: float | None = None


@dataclass
class Snapshot:
    """Everything an alert might need to evaluate one symbol at a point in time."""

    price: float | None = None
    change_percent: float | None = None
    volume: float | None = None
    indicators: Indicators | None = None


def _crossed_up(prev_a, prev_b, a, b) -> bool:
    return None not in (prev_a, prev_b, a, b) and prev_a <= prev_b and a > b


def _crossed_down(prev_a, prev_b, a, b) -> bool:
    return None not in (prev_a, prev_b, a, b) and prev_a >= prev_b and a < b


def evaluate(alert: Alert, snap: Snapshot) -> str | None:
    """Return a trigger message if the alert's condition is met, else ``None``."""
    t = alert.type
    thr = alert.threshold
    ind = snap.indicators or Indicators()

    if t is AlertType.PRICE_ABOVE and snap.price is not None and thr is not None:
        if snap.price >= thr:
            return f"Price {snap.price:g} crossed above {thr:g}"
    elif t is AlertType.PRICE_BELOW and snap.price is not None and thr is not None:
        if snap.price <= thr:
            return f"Price {snap.price:g} fell below {thr:g}"
    elif t is AlertType.PERCENT_UP and snap.change_percent is not None and thr is not None:
        if snap.change_percent >= thr:
            return f"Up {snap.change_percent:.2f}% today (≥ {thr:g}%)"
    elif t is AlertType.PERCENT_DOWN and snap.change_percent is not None and thr is not None:
        if snap.change_percent <= -abs(thr):
            return f"Down {snap.change_percent:.2f}% today (≤ -{abs(thr):g}%)"
    elif t is AlertType.VOLUME_ABOVE and snap.volume is not None and thr is not None:
        if snap.volume >= thr:
            return f"Volume {snap.volume:.0f} above {thr:g}"
    elif t is AlertType.RSI_ABOVE and ind.rsi is not None and thr is not None:
        if ind.rsi >= thr:
            return f"RSI {ind.rsi:.1f} above {thr:g}"
    elif t is AlertType.RSI_BELOW and ind.rsi is not None and thr is not None:
        if ind.rsi <= thr:
            return f"RSI {ind.rsi:.1f} below {thr:g}"
    elif t is AlertType.MACD_CROSS_UP:
        if _crossed_up(ind.macd_prev, ind.signal_prev, ind.macd, ind.signal):
            return "MACD crossed above signal (bullish)"
    elif t is AlertType.MACD_CROSS_DOWN:
        if _crossed_down(ind.macd_prev, ind.signal_prev, ind.macd, ind.signal):
            return "MACD crossed below signal (bearish)"
    elif t is AlertType.GOLDEN_CROSS:
        if _crossed_up(ind.sma_fast_prev, ind.sma_slow_prev, ind.sma_fast, ind.sma_slow):
            return "Golden cross — fast SMA crossed above slow SMA"
    elif t is AlertType.DEATH_CROSS:
        if _crossed_down(ind.sma_fast_prev, ind.sma_slow_prev, ind.sma_fast, ind.sma_slow):
            return "Death cross — fast SMA crossed below slow SMA"
    return None


def _last_two(series) -> tuple[float | None, float | None]:
    """Return (previous, latest) non-NaN-safe values of a pandas Series."""
    vals = [float(v) for v in series.tolist()]
    prev = vals[-2] if len(vals) >= 2 else None
    latest = vals[-1] if vals else None
    # NaN → None
    prev = None if prev is None or prev != prev else prev
    latest = None if latest is None or latest != latest else latest
    return prev, latest


def build_indicators(
    candles: list[Candle], fast: int = 50, slow: int = 200
) -> Indicators:
    """Compute the scalar indicator values used by alert evaluation."""
    if not candles:
        return Indicators()
    frame = candles_to_frame(candles)
    close = frame["close"]

    rsi_prev, rsi = _last_two(calc_rsi(close, 14))
    macd = calc_macd(close)
    macd_prev, macd_now = _last_two(macd["macd"])
    sig_prev, sig_now = _last_two(macd["signal"])
    fast_prev, fast_now = _last_two(calc_sma(close, fast))
    slow_prev, slow_now = _last_two(calc_sma(close, slow))

    return Indicators(
        rsi=rsi,
        macd=macd_now,
        macd_prev=macd_prev,
        signal=sig_now,
        signal_prev=sig_prev,
        sma_fast=fast_now,
        sma_fast_prev=fast_prev,
        sma_slow=slow_now,
        sma_slow_prev=slow_prev,
    )
