"""Alert CRUD + triggered-event recording (Phase 7).

Direct ``session_scope`` style (like watchlists/portfolio). Cooldown gating and
condition evaluation live in the monitor + pure engine; this service owns
persistence: alert rows, ``last_triggered_at`` bookkeeping, and the event feed.
"""

from __future__ import annotations

from sqlalchemy import select

from app.alerts.schemas import Alert, AlertCreate, AlertEvent, AlertType, AlertUpdate
from app.db.base import utcnow
from app.db.models import AlertEventRow, AlertRow
from app.db.session import session_scope


class AlertService:
    def list(self) -> list[Alert]:
        with session_scope() as s:
            rows = (
                s.execute(select(AlertRow).order_by(AlertRow.symbol, AlertRow.id))
                .scalars()
                .all()
            )
            return [self._to_schema(r) for r in rows]

    def create(self, data: AlertCreate) -> Alert:
        with session_scope() as s:
            row = AlertRow(
                symbol=data.symbol.strip().upper(),
                type=data.type.value,
                threshold=data.threshold,
                params=data.params,
                active=True,
                cooldown_seconds=data.cooldown_seconds,
                note=data.note,
            )
            s.add(row)
            s.flush()
            return self._to_schema(row)

    def update(self, alert_id: int, data: AlertUpdate) -> Alert | None:
        with session_scope() as s:
            row = s.get(AlertRow, alert_id)
            if row is None:
                return None
            for field, value in data.model_dump(exclude_unset=True).items():
                setattr(row, field, value)
            s.flush()
            return self._to_schema(row)

    def delete(self, alert_id: int) -> bool:
        with session_scope() as s:
            row = s.get(AlertRow, alert_id)
            if row is None:
                return False
            s.delete(row)
            return True

    def active_grouped(self) -> dict[str, list[Alert]]:
        """Active alerts grouped by symbol (for the monitor's evaluation pass)."""
        with session_scope() as s:
            rows = (
                s.execute(select(AlertRow).where(AlertRow.active.is_(True)))
                .scalars()
                .all()
            )
        grouped: dict[str, list[Alert]] = {}
        for r in rows:
            grouped.setdefault(r.symbol, []).append(self._to_schema(r))
        return grouped

    def record_event(
        self, alert: Alert, message: str, price: float | None
    ) -> AlertEvent:
        """Stamp the alert as triggered now and persist an event; return it."""
        now = utcnow()
        with session_scope() as s:
            row = s.get(AlertRow, alert.id)
            if row is not None:
                row.last_triggered_at = now
            event = AlertEventRow(
                alert_id=alert.id,
                symbol=alert.symbol,
                type=alert.type.value,
                message=message,
                price=price,
                created_at=now,
            )
            s.add(event)
            s.flush()
            return AlertEvent(
                id=event.id,
                alert_id=event.alert_id,
                symbol=event.symbol,
                type=AlertType(event.type),
                message=event.message,
                price=event.price,
                created_at=event.created_at,
            )

    def recent_events(self, limit: int = 50) -> list[AlertEvent]:
        with session_scope() as s:
            rows = (
                s.execute(
                    select(AlertEventRow)
                    .order_by(AlertEventRow.created_at.desc(), AlertEventRow.id.desc())
                    .limit(limit)
                )
                .scalars()
                .all()
            )
            return [
                AlertEvent(
                    id=r.id,
                    alert_id=r.alert_id,
                    symbol=r.symbol,
                    type=AlertType(r.type),
                    message=r.message,
                    price=r.price,
                    created_at=r.created_at,
                )
                for r in rows
            ]

    @staticmethod
    def _to_schema(row: AlertRow) -> Alert:
        return Alert(
            id=row.id,
            symbol=row.symbol,
            type=AlertType(row.type),
            threshold=row.threshold,
            params=row.params,
            active=row.active,
            cooldown_seconds=row.cooldown_seconds,
            note=row.note,
            last_triggered_at=row.last_triggered_at,
        )
