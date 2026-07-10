"""Scheduler & reports API routes (Phase 8).

* ``GET  /api/v1/scheduler/status``              — scheduler health + next runs
* ``GET  /api/v1/reports/morning``               — latest morning summary (by region)
* ``POST /api/v1/reports/morning/generate``      — trigger generation on demand
* ``GET  /api/v1/reports/watch``                 — latest stocks-to-watch digest
* ``POST /api/v1/reports/watch/generate``        — trigger digest on demand
* ``GET  /api/v1/calendar``                        — upcoming economic events
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.scheduler import (
    MorningSummary,
    ReportRegion,
    ReportService,
    SchedulerManager,
    StocksToWatchDigest,
)
from app.scheduler.calendar import build_economic_calendar
from app.scheduler.schemas import EconomicCalendar

from .deps import get_report_service, get_scheduler_manager

router = APIRouter(tags=["scheduler"])

ReportDep = Annotated[ReportService, Depends(get_report_service)]
SchedulerDep = Annotated[SchedulerManager, Depends(get_scheduler_manager)]


@router.get("/api/v1/scheduler/status", summary="Scheduler status")
def scheduler_status(manager: SchedulerDep):
    return manager.status()


@router.get(
    "/api/v1/reports/morning",
    response_model=MorningSummary,
    summary="Latest morning market summary",
)
async def get_morning_summary(
    service: ReportDep,
    region: Annotated[ReportRegion, Query()] = ReportRegion.US,
) -> MorningSummary:
    summary = service.latest_morning(region)
    if summary is None:
        return await service.generate_morning(region)
    return summary


@router.post(
    "/api/v1/reports/morning/generate",
    response_model=MorningSummary,
    summary="Generate morning market summary now",
)
async def generate_morning_summary(
    service: ReportDep,
    region: Annotated[ReportRegion, Query()] = ReportRegion.US,
) -> MorningSummary:
    return await service.generate_morning(region)


@router.get(
    "/api/v1/reports/watch",
    response_model=StocksToWatchDigest,
    summary="Latest stocks-to-watch digest",
)
async def get_stocks_to_watch(service: ReportDep) -> StocksToWatchDigest:
    digest = service.latest_stocks_to_watch()
    if digest is None:
        return await service.generate_stocks_to_watch()
    return digest


@router.post(
    "/api/v1/reports/watch/generate",
    response_model=StocksToWatchDigest,
    summary="Generate stocks-to-watch digest now",
)
async def generate_stocks_to_watch(service: ReportDep) -> StocksToWatchDigest:
    return await service.generate_stocks_to_watch()


@router.get(
    "/api/v1/calendar",
    response_model=EconomicCalendar,
    summary="Upcoming economic calendar events",
)
def economic_calendar(
    days: Annotated[int, Query(ge=1, le=60)] = 14,
) -> EconomicCalendar:
    return build_economic_calendar(days=days)
