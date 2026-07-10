"""Tests for the volume profile (volume-by-price)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.data.models import Candle
from app.technical import compute_volume_profile


def _candle(i: int, low: float, high: float, volume: float) -> Candle:
    t = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=i)
    mid = (low + high) / 2
    return Candle(time=t, open=mid, high=high, low=low, close=mid, volume=volume)


def test_empty_candles() -> None:
    out = compute_volume_profile("AAPL", "1d", [], bins=10)
    assert out.bins == []
    assert out.poc is None
    assert out.max_volume == 0.0


def test_bins_span_full_range() -> None:
    candles = [_candle(0, 10.0, 20.0, 100.0), _candle(1, 12.0, 18.0, 50.0)]
    out = compute_volume_profile("AAPL", "1d", candles, bins=10)
    assert len(out.bins) == 10
    assert out.bins[0].low == 10.0
    assert out.bins[-1].high == 20.0
    # Bins are contiguous and ascending.
    for a, b in zip(out.bins, out.bins[1:], strict=False):
        assert b.low == a.high


def test_volume_conserved() -> None:
    candles = [_candle(0, 10.0, 20.0, 100.0), _candle(1, 14.0, 16.0, 40.0)]
    out = compute_volume_profile("AAPL", "1d", candles, bins=20)
    assert sum(b.volume for b in out.bins) == 140.0


def test_poc_at_most_traded_level() -> None:
    # Many candles concentrate volume around price 15.
    candles = [_candle(0, 10.0, 20.0, 10.0)]
    candles += [_candle(i + 1, 14.5, 15.5, 100.0) for i in range(5)]
    out = compute_volume_profile("AAPL", "1d", candles, bins=10)
    poc_bins = [b for b in out.bins if b.poc]
    assert len(poc_bins) == 1
    assert poc_bins[0].low <= 15.0 <= poc_bins[0].high
    assert out.poc is not None and 14.0 <= out.poc <= 16.0
    assert out.max_volume == max(b.volume for b in out.bins)


def test_flat_range_collapses_to_one_level() -> None:
    candles = [_candle(0, 5.0, 5.0, 30.0), _candle(1, 5.0, 5.0, 20.0)]
    out = compute_volume_profile("AAPL", "1d", candles, bins=10)
    assert len(out.bins) == 1
    assert out.bins[0].poc is True
    assert out.bins[0].volume == 50.0
