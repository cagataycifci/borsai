"""WebSocket integration tests (Phase 10)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_ws_ping_pong(initialized_db) -> None:
    app = create_app()
    with TestClient(app) as client:
        with client.websocket_connect("/ws/stream") as ws:
            ws.send_json({"action": "ping"})
            frame = ws.receive_json()
            assert frame == {"type": "pong"}


def test_ws_subscribe_quote_frame_shape(initialized_db) -> None:
    """Subscribe is accepted; we only assert the session doesn't error."""
    app = create_app()
    with TestClient(app) as client:
        with client.websocket_connect("/ws/stream") as ws:
            ws.send_json({"action": "subscribe", "symbols": ["AAPL"]})
            # May or may not receive a quote quickly (network); just ensure no error frame.
            ws.send_json({"action": "ping"})
            assert ws.receive_json()["type"] == "pong"
