"""APScheduler background job runner (Phase 8).

Registers cron/interval jobs for news refresh, morning summaries (US/TR/global),
and the stocks-to-watch digest. Started in the app lifespan alongside the alert
monitor (which keeps its own tight 15s loop for responsiveness).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.logging import get_logger
from app.news.service import NewsService
from app.scheduler.schemas import ReportRegion, SchedulerJobInfo, SchedulerStatus
from app.scheduler.service import ReportService

logger = get_logger(__name__)


@dataclass
class JobContext:
    reports: ReportService
    news: NewsService


class SchedulerManager:
    """Owns the APScheduler instance and registered background jobs."""

    def __init__(self, ctx: JobContext) -> None:
        self._ctx = ctx
        self._scheduler = AsyncIOScheduler(timezone="UTC")

    def start(self) -> None:
        if self._scheduler.running:
            return

        # News refresh every 4 hours (off the request path).
        self._scheduler.add_job(
            _job(self._ctx.news.refresh),
            IntervalTrigger(hours=4),
            id="news_refresh",
            name="News refresh",
            replace_existing=True,
        )

        # Morning summaries — US ~13:30 UTC (post US pre-market), TR 07:00 UTC,
        # global overview at 06:00 UTC.
        self._scheduler.add_job(
            _job(lambda: self._ctx.reports.generate_morning(ReportRegion.US)),
            CronTrigger(hour=13, minute=30),
            id="morning_us",
            name="US morning summary",
            replace_existing=True,
        )
        self._scheduler.add_job(
            _job(lambda: self._ctx.reports.generate_morning(ReportRegion.TR)),
            CronTrigger(hour=7, minute=0),
            id="morning_tr",
            name="BIST morning summary",
            replace_existing=True,
        )
        self._scheduler.add_job(
            _job(lambda: self._ctx.reports.generate_morning(ReportRegion.GLOBAL)),
            CronTrigger(hour=6, minute=0),
            id="morning_global",
            name="Global morning summary",
            replace_existing=True,
        )

        # Stocks-to-watch digest shortly after US cash open.
        self._scheduler.add_job(
            _job(self._ctx.reports.generate_stocks_to_watch),
            CronTrigger(hour=14, minute=30),
            id="stocks_to_watch",
            name="Stocks to watch",
            replace_existing=True,
        )

        self._scheduler.start()
        logger.info("Scheduler started with %d jobs", len(self._scheduler.get_jobs()))

    def stop(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

    def status(self) -> SchedulerStatus:
        jobs = [
            SchedulerJobInfo(
                id=job.id or "",
                name=job.name or job.id or "",
                next_run=job.next_run_time,
            )
            for job in self._scheduler.get_jobs()
        ]
        return SchedulerStatus(running=self._scheduler.running, jobs=jobs)


def _job(coro_factory: Callable[[], Awaitable[object]]):
    """Wrap an async callable so APScheduler can await it."""

    async def _run() -> None:
        try:
            await coro_factory()
        except Exception as exc:  # noqa: BLE001 — jobs must not crash the scheduler
            logger.warning("Scheduled job failed: %s", exc)

    return _run
