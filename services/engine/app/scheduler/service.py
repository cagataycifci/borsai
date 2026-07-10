"""Report persistence + orchestration (Phase 8)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.ai.factory import build_ai_provider
from app.alerts.monitor import ConnectionHub
from app.core.logging import get_logger
from app.data.service import MarketDataService
from app.db.base import utcnow
from app.db.models import ScheduledReportRow
from app.db.session import session_scope
from app.news.service import NewsService
from app.portfolio.service import PortfolioService
from app.scheduler.schemas import (
    MorningSummary,
    ReportKind,
    ReportRegion,
    ScheduledReport,
    StocksToWatchDigest,
)
from app.scheduler.summary import build_morning_summary
from app.scheduler.watch_digest import build_stocks_to_watch
from app.settings.service import SecretsService, SettingsService
from app.watchlists.service import WatchlistService

logger = get_logger(__name__)

_REGION_KIND: dict[ReportRegion, ReportKind] = {
    ReportRegion.US: ReportKind.MORNING_US,
    ReportRegion.TR: ReportKind.MORNING_TR,
    ReportRegion.GLOBAL: ReportKind.MORNING_GLOBAL,
}


class ReportService:
    def __init__(
        self,
        market: MarketDataService,
        news: NewsService,
        watchlists: WatchlistService,
        portfolio: PortfolioService,
        settings: SettingsService,
        secrets: SecretsService,
        ws_hub: ConnectionHub | None = None,
    ) -> None:
        self._market = market
        self._news = news
        self._watchlists = watchlists
        self._portfolio = portfolio
        self._settings = settings
        self._secrets = secrets
        self._hub = ws_hub

    async def generate_morning(self, region: ReportRegion) -> MorningSummary:
        provider = build_ai_provider(self._settings, self._secrets)
        summary = await build_morning_summary(
            region, self._market, self._news, ai_provider=provider
        )
        kind = _REGION_KIND[region]
        self._persist(kind, summary.model_dump(mode="json"))
        await self._broadcast_report(kind, summary.model_dump(mode="json"))
        logger.info("Morning summary generated: %s", region.value)
        return summary

    async def generate_stocks_to_watch(self) -> StocksToWatchDigest:
        digest = await build_stocks_to_watch(
            self._watchlists, self._portfolio, self._market
        )
        self._persist(ReportKind.STOCKS_TO_WATCH, digest.model_dump(mode="json"))
        await self._broadcast_report(ReportKind.STOCKS_TO_WATCH, digest.model_dump(mode="json"))
        logger.info("Stocks-to-watch digest generated (%d picks)", len(digest.picks))
        return digest

    def latest_morning(self, region: ReportRegion) -> MorningSummary | None:
        kind = _REGION_KIND[region]
        row = self._latest_row(kind)
        if row is None:
            return None
        return MorningSummary.model_validate(row.payload)

    def latest_stocks_to_watch(self) -> StocksToWatchDigest | None:
        row = self._latest_row(ReportKind.STOCKS_TO_WATCH)
        if row is None:
            return None
        return StocksToWatchDigest.model_validate(row.payload)

    def list_reports(
        self, kind: ReportKind | None = None, limit: int = 10
    ) -> list[ScheduledReport]:
        with session_scope() as s:
            q = select(ScheduledReportRow).order_by(ScheduledReportRow.created_at.desc())
            if kind is not None:
                q = q.where(ScheduledReportRow.kind == kind.value)
            rows = s.execute(q.limit(limit)).scalars().all()
            return [self._to_schema(r) for r in rows]

    def _persist(self, kind: ReportKind, payload: dict[str, Any]) -> ScheduledReport:
        with session_scope() as s:
            row = ScheduledReportRow(kind=kind.value, payload=payload, created_at=utcnow())
            s.add(row)
            s.flush()
            return self._to_schema(row)

    def _latest_row(self, kind: ReportKind) -> ScheduledReportRow | None:
        with session_scope() as s:
            return (
                s.execute(
                    select(ScheduledReportRow)
                    .where(ScheduledReportRow.kind == kind.value)
                    .order_by(ScheduledReportRow.created_at.desc())
                    .limit(1)
                )
                .scalars()
                .first()
            )

    async def _broadcast_report(self, kind: ReportKind, payload: dict[str, Any]) -> None:
        if self._hub is None:
            return
        await self._hub.broadcast(
            {"type": "report", "data": {"kind": kind.value, "payload": payload}}
        )

    @staticmethod
    def _to_schema(row: ScheduledReportRow) -> ScheduledReport:
        return ScheduledReport(
            id=row.id,
            kind=ReportKind(row.kind),
            payload=row.payload,
            created_at=row.created_at,
        )
