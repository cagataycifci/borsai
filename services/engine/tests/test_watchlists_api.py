"""HTTP CRUD tests for the watchlists API (offline, real DB)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_watchlist_crud(initialized_db) -> None:
    app = create_app()
    with TestClient(app) as client:
        # A starter watchlist is seeded on first run.
        lists = client.get("/api/v1/watchlists").json()
        assert len(lists) == 1
        assert len(lists[0]["symbols"]) == 7

        # Create a new (empty) watchlist.
        tech = client.post("/api/v1/watchlists", json={"name": "Tech"}).json()
        tid = tech["id"]
        assert tech["name"] == "Tech"
        assert tech["symbols"] == []

        # Add symbols (normalized to upper-case, deduped).
        client.post(f"/api/v1/watchlists/{tid}/items", json={"symbol": "aapl"})
        dup = client.post(f"/api/v1/watchlists/{tid}/items", json={"symbol": "AAPL"}).json()
        assert dup["symbols"] == ["AAPL"]
        client.post(f"/api/v1/watchlists/{tid}/items", json={"symbol": "MSFT"})

        # Reorder.
        reordered = client.put(
            f"/api/v1/watchlists/{tid}/items", json={"symbols": ["MSFT", "AAPL"]}
        ).json()
        assert reordered["symbols"] == ["MSFT", "AAPL"]

        # Remove a symbol.
        removed = client.delete(f"/api/v1/watchlists/{tid}/items/AAPL").json()
        assert removed["symbols"] == ["MSFT"]

        # Rename.
        renamed = client.put(f"/api/v1/watchlists/{tid}", json={"name": "Tech2"}).json()
        assert renamed["name"] == "Tech2"

        # Delete (cascades items) → back to just the default list.
        assert client.delete(f"/api/v1/watchlists/{tid}").status_code == 200
        assert len(client.get("/api/v1/watchlists").json()) == 1

        # Unknown id → 404.
        assert client.delete("/api/v1/watchlists/9999").status_code == 404
        assert client.put("/api/v1/watchlists/9999", json={"name": "x"}).status_code == 404
