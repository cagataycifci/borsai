"""Alert domain models + API schemas (Phase 7).

Mirrored in ``renderer/src/lib/contracts.ts``. An alert is a condition on one
symbol; when the engine's monitor evaluates it to true (respecting a cooldown) it
emits an :class:`AlertEvent`, pushed over the WebSocket and persisted for a feed.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class AlertType(StrEnum):
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    PERCENT_UP = "percent_up"  # day change_percent >= threshold
    PERCENT_DOWN = "percent_down"  # day change_percent <= -threshold
    VOLUME_ABOVE = "volume_above"
    RSI_ABOVE = "rsi_above"
    RSI_BELOW = "rsi_below"
    MACD_CROSS_UP = "macd_cross_up"  # MACD crosses above its signal line
    MACD_CROSS_DOWN = "macd_cross_down"  # MACD crosses below its signal line
    GOLDEN_CROSS = "golden_cross"  # fast SMA crosses above slow SMA
    DEATH_CROSS = "death_cross"  # fast SMA crosses below slow SMA


#: Alert types that require indicator computation (history fetch) to evaluate.
TECHNICAL_TYPES: frozenset[AlertType] = frozenset(
    {
        AlertType.RSI_ABOVE,
        AlertType.RSI_BELOW,
        AlertType.MACD_CROSS_UP,
        AlertType.MACD_CROSS_DOWN,
        AlertType.GOLDEN_CROSS,
        AlertType.DEATH_CROSS,
    }
)

#: Alert types that need a numeric threshold.
THRESHOLD_TYPES: frozenset[AlertType] = frozenset(
    {
        AlertType.PRICE_ABOVE,
        AlertType.PRICE_BELOW,
        AlertType.PERCENT_UP,
        AlertType.PERCENT_DOWN,
        AlertType.VOLUME_ABOVE,
        AlertType.RSI_ABOVE,
        AlertType.RSI_BELOW,
    }
)


class Alert(BaseModel):
    id: int
    symbol: str
    type: AlertType
    threshold: float | None = None
    params: dict[str, float] | None = None
    active: bool = True
    cooldown_seconds: int = 3600
    note: str | None = None
    last_triggered_at: datetime | None = None


class AlertCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    type: AlertType
    threshold: float | None = None
    params: dict[str, float] | None = None
    cooldown_seconds: int = Field(default=3600, ge=0)
    note: str | None = Field(default=None, max_length=256)


class AlertUpdate(BaseModel):
    threshold: float | None = None
    params: dict[str, float] | None = None
    active: bool | None = None
    cooldown_seconds: int | None = Field(default=None, ge=0)
    note: str | None = Field(default=None, max_length=256)


class AlertEvent(BaseModel):
    id: int | None = None
    alert_id: int | None = None
    symbol: str
    type: AlertType
    message: str
    price: float | None = None
    created_at: datetime | None = None
