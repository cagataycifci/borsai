"""HTTP tests for the alerts API (real DB, no network)."""

from __future__ import annotations

from app.alerts import Alert
from app.main import create_app
from fastapi.testclient import TestClient


def test_alerts_crud_and_events(initialized_db) -> None:
    app = create_app()
    with TestClient(app) as client:
        # Create a threshold alert.
        created = client.post(
            "/api/v1/alerts",
            json={"symbol": "aapl", "type": "price_above", "threshold": 200},
        )
        assert created.status_code == 200
        alert = created.json()
        assert alert["symbol"] == "AAPL"
        assert alert["active"] is True

        # A threshold type without a threshold is rejected.
        assert (
            client.post(
                "/api/v1/alerts", json={"symbol": "AAPL", "type": "price_below"}
            ).status_code
            == 400
        )

        # A cross alert needs no threshold.
        assert (
            client.post(
                "/api/v1/alerts", json={"symbol": "MSFT", "type": "golden_cross"}
            ).status_code
            == 200
        )

        assert len(client.get("/api/v1/alerts").json()) == 2

        # Deactivate the first alert.
        upd = client.put(f"/api/v1/alerts/{alert['id']}", json={"active": False}).json()
        assert upd["active"] is False
        assert client.put("/api/v1/alerts/9999", json={"active": False}).status_code == 404

        # Events feed: simulate a trigger through the live service, then read it.
        app.state.alert_service.record_event(Alert(**alert), "Price 250 above 200", 250.0)
        events = client.get("/api/v1/alerts/events").json()
        assert len(events) == 1
        assert events[0]["symbol"] == "AAPL"
        assert events[0]["price"] == 250.0

        # Delete.
        assert client.delete(f"/api/v1/alerts/{alert['id']}").json()["deleted"] is True
        assert len(client.get("/api/v1/alerts").json()) == 1
