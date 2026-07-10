"""Pydantic schemas for scheduled reports and the economic calendar (Phase 8)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ReportRegion(StrEnum):
    US = "us"
    TR = "tr"
    GLOBAL = "global"


class ReportKind(StrEnum):
    MORNING_US = "morning_us"
    MORNING_TR = "morning_tr"
    MORNING_GLOBAL = "morning_global"
    STOCKS_TO_WATCH = "stocks_to_watch"


class QuoteSnapshot(BaseModel):
    symbol: str
    display_symbol: str
    name: str | None = None
    price: float | None = None
    change: float | None = None
    change_percent: float | None = None
    currency: str = "USD"


class NewsHeadline(BaseModel):
    title: str
    source: str
    url: str


class MorningSummary(BaseModel):
    region: ReportRegion
    title: str
    overview: str
    benchmarks: list[QuoteSnapshot] = Field(default_factory=list)
    headlines: list[NewsHeadline] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    ai_enhanced: bool = False
    generated_at: datetime


class WatchPick(BaseModel):
    symbol: str
    display_symbol: str
    name: str | None = None
    price: float | None = None
    change_percent: float | None = None
    reason: str


class StocksToWatchDigest(BaseModel):
    title: str = "Stocks to Watch"
    overview: str
    picks: list[WatchPick] = Field(default_factory=list)
    generated_at: datetime


class EconomicEvent(BaseModel):
    title: str
    country: str  # US, TR, EU, GLOBAL
    impact: str  # low, medium, high
    event_at: datetime
    category: str | None = None


class EconomicCalendar(BaseModel):
    events: list[EconomicEvent] = Field(default_factory=list)
    from_date: datetime
    to_date: datetime


class ScheduledReport(BaseModel):
    id: int
    kind: ReportKind
    payload: dict[str, Any]
    created_at: datetime


class SchedulerJobInfo(BaseModel):
    id: str
    name: str
    next_run: datetime | None = None


class SchedulerStatus(BaseModel):
    running: bool
    jobs: list[SchedulerJobInfo] = Field(default_factory=list)
