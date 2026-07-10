"""Technical analysis: OHLCV resampling and indicators (Phase 3).

This package is intentionally provider-agnostic — it operates on the canonical
:class:`app.data.models.Candle` shape, never on raw provider payloads, so it can
be reused by charts, alerts, and AI features alike.
"""

from app.technical.indicators import (
    IndicatorResponse,
    IndicatorSeries,
    compute_indicators,
)
from app.technical.resample import resample_candles
from app.technical.volume_profile import (
    VolumeBin,
    VolumeProfileResponse,
    compute_volume_profile,
)

__all__ = [
    "IndicatorResponse",
    "IndicatorSeries",
    "VolumeBin",
    "VolumeProfileResponse",
    "compute_indicators",
    "compute_volume_profile",
    "resample_candles",
]
