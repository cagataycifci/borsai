"""OHLCV candle resampling.

yfinance (and most free providers) expose a fixed set of native intervals; 4h in
particular is not offered. We synthesize coarser bars from finer ones with the
standard OHLCV aggregation (open=first, high=max, low=min, close=last,
volume=sum). The service layer fetches 1h candles and resamples them to 4h, but
the helper is generic so any rule (e.g. ``"4h"``, ``"2h"``, ``"1D"``) works.
"""

from __future__ import annotations

import pandas as pd

from app.data.models import Candle

# Standard OHLCV aggregation for downsampling a finer series into a coarser one.
_AGG: dict[str, str] = {
    "open": "first",
    "high": "max",
    "low": "min",
    "close": "last",
    "volume": "sum",
}


def resample_candles(candles: list[Candle], rule: str) -> list[Candle]:
    """Aggregate a sorted list of candles into coarser bars.

    ``rule`` is a pandas offset alias (e.g. ``"4h"``). Empty input yields an
    empty list. Buckets with no source bar are dropped so the result has no gaps
    of synthetic NaN candles. Bars are left-labelled/left-closed: a bar stamped
    ``08:00`` covers ``[08:00, 12:00)`` for a ``4h`` rule.
    """
    if not candles:
        return []

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

    agg = (
        frame.resample(rule, label="left", closed="left")
        .agg(_AGG)
        .dropna(subset=["open"])
    )

    return [
        Candle(
            time=ts.to_pydatetime(),
            open=float(row.open),
            high=float(row.high),
            low=float(row.low),
            close=float(row.close),
            volume=float(row.volume),
        )
        for ts, row in agg.iterrows()
    ]
