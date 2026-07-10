"""Alert monitor: periodic evaluation + WebSocket broadcast (Phase 7).

A single background task (started in the app lifespan) evaluates every active
alert on an interval and pushes ``{"type": "alert", "data": <AlertEvent>}`` frames
to all connected WebSocket clients via the :class:`ConnectionHub`. Data is delayed
at the free tier, so polling the cache-backed :class:`MarketDataService` (rather
than a true push feed) matches the existing quote-streaming design.

Full scheduling (APScheduler, cron reports) arrives in Phase 8; this is the
minimal always-on evaluator alerts need now.
"""

from __future__ import annotations

import asyncio
import contextlib

from fastapi import WebSocket

from app.alerts.engine import Snapshot, build_indicators
from app.alerts.engine import evaluate as evaluate_alert
from app.alerts.schemas import TECHNICAL_TYPES, Alert
from app.alerts.service import AlertService
from app.core.logging import get_logger
from app.data.base import Interval, Range
from app.data.service import MarketDataService
from app.db.base import utcnow

logger = get_logger(__name__)

EVAL_INTERVAL_SECONDS = 15.0


class ConnectionHub:
    """Tracks connected WebSocket clients and fans a frame out to all of them."""

    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()

    def add(self, ws: WebSocket) -> None:
        self._clients.add(ws)

    def remove(self, ws: WebSocket) -> None:
        self._clients.discard(ws)

    async def broadcast(self, frame: dict) -> None:
        for ws in list(self._clients):
            try:
                await ws.send_json(frame)
            except Exception:  # noqa: BLE001 - drop dead sockets silently
                self._clients.discard(ws)


class AlertMonitor:
    def __init__(
        self, service: AlertService, market: MarketDataService, hub: ConnectionHub
    ) -> None:
        self._service = service
        self._market = market
        self._hub = hub
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _run(self) -> None:
        while True:
            try:
                await self._tick()
            except Exception as exc:  # noqa: BLE001 - never let the loop die
                logger.warning("Alert monitor tick failed: %s", exc)
            await asyncio.sleep(EVAL_INTERVAL_SECONDS)

    async def _tick(self) -> None:
        grouped = self._service.active_grouped()
        for symbol, alerts in grouped.items():
            await self._evaluate_symbol(symbol, alerts)

    async def _evaluate_symbol(self, symbol: str, alerts: list[Alert]) -> None:
        quote = await self._market.get_quote(symbol)
        indicators = None
        if any(a.type in TECHNICAL_TYPES for a in alerts):
            fast, slow = self._cross_periods(alerts)
            candles = await self._market.get_history(symbol, Interval.D1, Range.Y1)
            indicators = build_indicators(candles, fast, slow)

        snap = Snapshot(
            price=quote.price if quote else None,
            change_percent=quote.change_percent if quote else None,
            volume=quote.volume if quote else None,
            indicators=indicators,
        )
        now = utcnow()
        for alert in alerts:
            if not self._cooldown_elapsed(alert, now):
                continue
            message = evaluate_alert(alert, snap)
            if message is None:
                continue
            event = self._service.record_event(
                alert, message, quote.price if quote else None
            )
            await self._hub.broadcast(
                {"type": "alert", "data": event.model_dump(mode="json")}
            )
            logger.info("Alert fired: %s %s — %s", symbol, alert.type, message)

    @staticmethod
    def _cross_periods(alerts: list[Alert]) -> tuple[int, int]:
        """Pick SMA fast/slow periods from the first cross alert, else 50/200."""
        for a in alerts:
            if a.type.value in {"golden_cross", "death_cross"} and a.params:
                return int(a.params.get("fast", 50)), int(a.params.get("slow", 200))
        return 50, 200

    @staticmethod
    def _cooldown_elapsed(alert: Alert, now) -> bool:
        if alert.last_triggered_at is None:
            return True
        return (now - alert.last_triggered_at).total_seconds() >= alert.cooldown_seconds
