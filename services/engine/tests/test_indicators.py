"""Tests for technical indicators."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd

from app.data.models import Candle
from app.technical import compute_indicators
from app.technical.indicators import (
    calc_atr,
    calc_ema,
    calc_rsi,
    calc_sma,
    candles_to_frame,
)


def _series(closes: list[float]) -> list[Candle]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    out: list[Candle] = []
    for i, c in enumerate(closes):
        out.append(
            Candle(
                time=start + timedelta(days=i),
                open=c,
                high=c + 1,
                low=c - 1,
                close=c,
                volume=1000.0,
            )
        )
    return out


def test_sma_matches_manual_mean() -> None:
    closes = [1, 2, 3, 4, 5, 6]
    frame = candles_to_frame(_series(closes))
    sma = calc_sma(frame["close"], 3)
    assert pd.isna(sma.iloc[0]) and pd.isna(sma.iloc[1])
    assert sma.iloc[2] == 2.0  # mean(1,2,3)
    assert sma.iloc[5] == 5.0  # mean(4,5,6)


def test_ema_first_value_after_warmup() -> None:
    closes = [10, 11, 12, 13, 14]
    frame = candles_to_frame(_series(closes))
    ema = calc_ema(frame["close"], 3)
    # First two are warm-up NaN; third onward defined and finite.
    assert pd.isna(ema.iloc[1])
    assert ema.iloc[2:].notna().all()


def test_rsi_all_gains_approaches_100() -> None:
    closes = list(range(1, 30))  # strictly increasing → no losses
    frame = candles_to_frame(_series([float(c) for c in closes]))
    rsi = calc_rsi(frame["close"], 14)
    assert rsi.dropna().iloc[-1] > 99.0


def test_atr_is_positive() -> None:
    closes = [10, 12, 11, 13, 12, 14, 13, 15, 14, 16, 15, 17, 16, 18, 17, 19]
    frame = candles_to_frame(_series([float(c) for c in closes]))
    atr = calc_atr(frame, 14)
    assert atr.dropna().iloc[-1] > 0


def test_compute_indicators_spec_parsing_and_panes() -> None:
    candles = _series([float(c) for c in range(1, 60)])
    resp = compute_indicators(
        "TEST", "1d", candles, "sma:20,ema:50,rsi,macd,bbands:20:2,vwap,stoch,atr"
    )
    keys = {s.key for s in resp.series}
    assert "sma_20" in keys
    assert "ema_50" in keys
    assert "rsi_14" in keys
    assert {"macd", "macd_signal", "macd_hist"} <= keys
    assert {"bb_upper", "bb_middle", "bb_lower"} <= keys
    assert "vwap" in keys
    assert {"stoch_k", "stoch_d"} <= keys

    panes = {s.key: s.pane for s in resp.series}
    assert panes["sma_20"] == "price"
    assert panes["rsi_14"] == "rsi"
    assert panes["macd"] == "macd"

    # NaN must be serialized as None (JSON-safe), never NaN.
    for s in resp.series:
        for p in s.points:
            assert p.value is None or isinstance(p.value, float)


def test_compute_indicators_empty_candles() -> None:
    resp = compute_indicators("TEST", "1d", [], "sma:20")
    assert resp.series == []
