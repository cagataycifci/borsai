"""Tests for settings & secrets services."""

from __future__ import annotations


def test_settings_roundtrip(initialized_db) -> None:
    from app.settings.service import SettingsService

    svc = SettingsService()
    assert svc.get("missing", "default") == "default"
    svc.set("ui.theme", "dark")
    assert svc.get("ui.theme") == "dark"
    svc.set("ui.theme", {"mode": "dark", "accent": "blue"})
    assert svc.get("ui.theme") == {"mode": "dark", "accent": "blue"}
    assert "ui.theme" in svc.all()


def test_provider_order_defaults_and_set(initialized_db) -> None:
    from app.settings.service import DEFAULT_PROVIDER_ORDER, SettingsService

    svc = SettingsService()
    assert svc.get_provider_order() == DEFAULT_PROVIDER_ORDER
    # Unknown providers are filtered out.
    cleaned = svc.set_provider_order(["finnhub", "bogus", "yfinance"])
    assert cleaned == ["finnhub", "yfinance"]
    assert svc.get_provider_order() == ["finnhub", "yfinance"]


def test_secrets_encrypted_roundtrip(initialized_db) -> None:
    from app.settings.service import SecretsService

    svc = SecretsService()
    assert svc.is_configured("finnhub") is False
    svc.set("finnhub", "super-secret-key")
    assert svc.is_configured("finnhub") is True
    assert svc.get("finnhub") == "super-secret-key"
    assert svc.status()["finnhub"] is True

    # Stored ciphertext must not equal the plaintext.
    from app.db.models import SecretRow
    from app.db.session import session_scope

    with session_scope() as s:
        row = s.get(SecretRow, "finnhub")
        assert row is not None
        assert row.ciphertext != "super-secret-key"

    assert svc.delete("finnhub") is True
    assert svc.is_configured("finnhub") is False


def test_unknown_provider_rejected(initialized_db) -> None:
    import pytest

    from app.settings.service import SecretsService

    with pytest.raises(ValueError):
        SecretsService().set("not-a-provider", "x")
