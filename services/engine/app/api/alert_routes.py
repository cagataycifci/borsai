"""Alert API routes (Phase 7).

* ``GET    /api/v1/alerts``          — list all alerts
* ``POST   /api/v1/alerts``          — create an alert
* ``PUT    /api/v1/alerts/{id}``     — update / (de)activate an alert
* ``DELETE /api/v1/alerts/{id}``     — delete an alert
* ``GET    /api/v1/alerts/events``   — recent triggered-event feed

Fired alerts are pushed live over ``WS /ws/stream`` by the alert monitor.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.alerts import Alert, AlertCreate, AlertEvent, AlertService, AlertUpdate
from app.alerts.schemas import THRESHOLD_TYPES

from .deps import get_alert_service

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])

AlertDep = Annotated[AlertService, Depends(get_alert_service)]


@router.get("", response_model=list[Alert], summary="List alerts")
def list_alerts(service: AlertDep) -> list[Alert]:
    return service.list()


@router.get("/events", response_model=list[AlertEvent], summary="Recent alert events")
def list_events(
    service: AlertDep, limit: Annotated[int, Query(ge=1, le=200)] = 50
) -> list[AlertEvent]:
    return service.recent_events(limit=limit)


@router.post("", response_model=Alert, summary="Create an alert")
def create_alert(service: AlertDep, body: AlertCreate) -> Alert:
    if body.type in THRESHOLD_TYPES and body.threshold is None:
        raise HTTPException(
            status_code=400, detail=f"Alert type '{body.type}' requires a threshold"
        )
    return service.create(body)


@router.put("/{alert_id}", response_model=Alert, summary="Update an alert")
def update_alert(service: AlertDep, alert_id: int, body: AlertUpdate) -> Alert:
    alert = service.update(alert_id, body)
    if alert is None:
        raise HTTPException(status_code=404, detail=f"No alert {alert_id}")
    return alert


@router.delete("/{alert_id}", summary="Delete an alert")
def delete_alert(service: AlertDep, alert_id: int) -> dict[str, bool]:
    return {"deleted": service.delete(alert_id)}
