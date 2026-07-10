"""Volume Profile — volume-by-price distribution over a candle series.

Buckets the price range spanned by the candles into ``bins`` equal-height price
levels and distributes each candle's volume across the levels its low–high range
overlaps. The level with the most accumulated volume is the Point of Control
(POC). Like the rest of :mod:`app.technical`, it operates on canonical
:class:`app.data.models.Candle` objects so it is reusable beyond charting.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.data.models import Candle


class VolumeBin(BaseModel):
    low: float  # bottom price of the level
    high: float  # top price of the level
    mid: float  # midpoint price (used for placement)
    volume: float  # accumulated volume in the level
    poc: bool = False  # True for the Point of Control (highest-volume level)


class VolumeProfileResponse(BaseModel):
    symbol: str
    interval: str
    bins: list[VolumeBin]
    poc: float | None  # midpoint price of the POC level
    max_volume: float  # largest bin volume (for renderer normalization)


def compute_volume_profile(
    symbol: str, interval: str, candles: list[Candle], bins: int = 24
) -> VolumeProfileResponse:
    """Build a volume-by-price profile with ``bins`` price levels."""
    bins = max(1, min(bins, 200))
    if not candles:
        return VolumeProfileResponse(
            symbol=symbol, interval=interval, bins=[], poc=None, max_volume=0.0
        )

    lo = min(c.low for c in candles)
    hi = max(c.high for c in candles)
    if hi <= lo:
        # Degenerate (flat) range — collapse to a single level.
        total = sum(c.volume for c in candles)
        return VolumeProfileResponse(
            symbol=symbol,
            interval=interval,
            bins=[VolumeBin(low=lo, high=hi, mid=lo, volume=total, poc=True)],
            poc=lo,
            max_volume=total,
        )

    step = (hi - lo) / bins
    volumes = [0.0] * bins

    for c in candles:
        # Spread the candle's volume evenly across the levels its range touches.
        start = int((c.low - lo) / step)
        end = int((c.high - lo) / step)
        start = max(0, min(start, bins - 1))
        end = max(0, min(end, bins - 1))
        span = end - start + 1
        share = c.volume / span
        for b in range(start, end + 1):
            volumes[b] += share

    poc_index = max(range(bins), key=lambda i: volumes[i])
    max_volume = volumes[poc_index]

    out = [
        VolumeBin(
            low=lo + i * step,
            high=lo + (i + 1) * step,
            mid=lo + (i + 0.5) * step,
            volume=volumes[i],
            poc=(i == poc_index),
        )
        for i in range(bins)
    ]
    return VolumeProfileResponse(
        symbol=symbol,
        interval=interval,
        bins=out,
        poc=out[poc_index].mid,
        max_volume=max_volume,
    )
