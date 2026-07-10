"""Alerts & notifications (Phase 7): user-defined price/technical alert conditions,
a pure evaluation engine, a CRUD service, and a background monitor that broadcasts
fired alerts over the WebSocket hub."""

from app.alerts.monitor import AlertMonitor, ConnectionHub
from app.alerts.schemas import (
    Alert,
    AlertCreate,
    AlertEvent,
    AlertType,
    AlertUpdate,
)
from app.alerts.service import AlertService

__all__ = [
    "Alert",
    "AlertCreate",
    "AlertEvent",
    "AlertMonitor",
    "AlertService",
    "AlertType",
    "AlertUpdate",
    "ConnectionHub",
]
