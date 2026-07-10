"""Tests for OHLCV candle resampling (1h → 4h)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.data.models import Candle
from app.technical import resample_candles


def _hourly(start: datetime, closes: list[float]) -> list[Candle]:
    """Build a contiguous hourly series whose OHLC derives from each close."""
    candles: list[Candle] = []
    for i, close in enumerate(closes):
        t = start + timedelta(hours=i)
        candles.append(
            Candle(
                time=t,
                open=close - 1,
                high=close + 2,
                low=close - 2,
                close=close,
                volume=100.0 + i,
            )
        )
    return candles


def test_resample_empty_returns_empty() -> None:
    assert resample_candles([], "4h") == []


def test_resample_1h_to_4h_aggregates_ohlcv() -> None:
    # 8 hourly bars at 00:00..07:00 → two 4h buckets [00:00, 04:00).
    start = datetime(2026, 6, 27, 0, 0, tzinfo=UTC)
    closes = [10, 12, 9, 11, 20, 25, 18, 22]
    out = resample_candles(_hourly(start, closes), "4h")

    assert len(out) == 2

    first, second = out
    assert first.time == start
    assert first.open == closes[0] - 1  # open of first bar in bucket
    assert first.close == closes[3]  # close of last bar in bucket
    assert first.high == max(c + 2 for c in closes[:4])
    assert first.low == min(c - 2 for c in closes[:4])
    assert first.volume == sum(100.0 + i for i in range(4))

    assert second.time == start + timedelta(hours=4)
    assert second.open == closes[4] - 1
    assert second.close == closes[7]
    assert second.high == max(c + 2 for c in closes[4:])
    assert second.low == min(c - 2 for c in closes[4:])


def test_resample_partial_bucket_kept() -> None:
    # 5 hourly bars → one full 4h bucket + one partial (single bar).
    start = datetime(2026, 6, 27, 0, 0, tzinfo=UTC)
    out = resample_candles(_hourly(start, [10, 11, 12, 13, 14]), "4h")
    assert len(out) == 2
    assert out[1].time == start + timedelta(hours=4)
    assert out[1].open == 14 - 1
    assert out[1].close == 14
