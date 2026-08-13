"""Tests for BIST KAP loader and API-key verification."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

_KAP_SAMPLE = [
    {
        "stockCode": "ACSEL",
        "kapMemberTitle": "ACISELSAN ACIPAYAM SELULOZ SANAYI VE TICARET A.S.",
        "payIslemDurumu": "1",
    },
    {
        "stockCode": "THYAO",
        "kapMemberTitle": "TURK HAVA YOLLARI A.O.",
        "payIslemDurumu": "1",
    },
    {
        "stockCode": "INACT",
        "kapMemberTitle": "INACTIVE CO",
        "payIslemDurumu": "0",
    },
    {"stockCode": "", "kapMemberTitle": "NO CODE", "payIslemDurumu": "1"},
]


@pytest.mark.asyncio
async def test_load_bist_full_parses_kap_response() -> None:
    from app.data.universe.loaders import load_bist_full

    client = MagicMock()
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = _KAP_SAMPLE
    client.get = AsyncMock(return_value=resp)

    rows = await load_bist_full(client)
    assert len(rows) == 2
    assert rows[0]["symbol"] == "ACSEL.IS"
    assert rows[0]["display_symbol"] == "ACSEL"
    assert rows[0]["source"] == "kap"
    assert rows[1]["display_symbol"] == "THYAO"


@pytest.mark.asyncio
async def test_load_bist_full_returns_empty_on_failure() -> None:
    from app.data.universe.loaders import load_bist_full

    client = MagicMock()
    client.get = AsyncMock(side_effect=RuntimeError("network down"))

    assert await load_bist_full(client) == []


@pytest.mark.asyncio
async def test_verify_finnhub_rejects_invalid_key(monkeypatch) -> None:
    from app.settings import validation as mod

    class FakeResp:
        status_code = 401

        def raise_for_status(self) -> None:
            pass

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, *args, **kwargs):
            return FakeResp()

    monkeypatch.setattr(mod.httpx, "AsyncClient", lambda **kwargs: FakeClient())

    ok, msg = await mod.verify_provider_key("finnhub", "bad-key")
    assert ok is False
    assert "Invalid" in msg


@pytest.mark.asyncio
async def test_verify_yfinance_is_keyless() -> None:
    from app.settings.validation import verify_provider_key

    ok, msg = await verify_provider_key("yfinance")
    assert ok is True
    assert "does not require" in msg


def test_verify_secret_route(initialized_db, monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from app.main import create_app
    from app.settings.service import SecretsService

    SecretsService().set("finnhub", "test-key")

    async def fake_verify(provider: str, api_key: str | None = None):
        return True, "ok"

    monkeypatch.setattr(
        "app.api.settings_routes.verify_provider_key",
        fake_verify,
    )

    client = TestClient(create_app())
    with client as c:
        resp = c.post("/api/v1/secrets/finnhub/verify")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["provider"] == "finnhub"
