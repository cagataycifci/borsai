"""Settings and secrets services.

- :class:`SettingsService` — JSON key/value app settings persisted in SQLite.
- :class:`SecretsService` — provider API keys, encrypted at rest with the
  :class:`~app.core.security.SecretBox`. Plaintext keys never leave the engine;
  the API only ever exposes a boolean "configured" status.
"""

from __future__ import annotations

from typing import Any

from app.core.security import get_secret_box
from app.db.models import SecretRow, SettingRow
from app.db.session import session_scope

# ---- Known providers -------------------------------------------------------
# Data providers and whether they require an API key.
DATA_PROVIDERS: dict[str, bool] = {
    "yfinance": False,  # no key required
    "finnhub": True,
}
# AI providers (used in Phase 6) — declared here so the secrets API accepts them.
AI_PROVIDERS: dict[str, bool] = {
    "anthropic": True,
    "openai": True,
    "gemini": True,
    "ollama": False,
}
KNOWN_PROVIDERS: dict[str, bool] = {**DATA_PROVIDERS, **AI_PROVIDERS}

# Settings keys.
KEY_PROVIDER_ORDER = "data.provider_order"
KEY_ACTIVE_AI_PROVIDER = "ai.active_provider"
KEY_AI_MODEL = "ai.model"  # optional per-provider model override

DEFAULT_PROVIDER_ORDER = ["finnhub", "yfinance"]
DEFAULT_AI_PROVIDER = "anthropic"


class SettingsService:
    def get(self, key: str, default: Any = None) -> Any:
        with session_scope() as s:
            row = s.get(SettingRow, key)
            return row.value if row is not None else default

    def set(self, key: str, value: Any) -> None:
        with session_scope() as s:
            row = s.get(SettingRow, key)
            if row is None:
                s.add(SettingRow(key=key, value=value))
            else:
                row.value = value

    def all(self) -> dict[str, Any]:
        with session_scope() as s:
            return {r.key: r.value for r in s.query(SettingRow).all()}

    def get_provider_order(self) -> list[str]:
        order = self.get(KEY_PROVIDER_ORDER)
        if not isinstance(order, list) or not order:
            return list(DEFAULT_PROVIDER_ORDER)
        # Keep only known data providers, preserving requested order.
        return [p for p in order if p in DATA_PROVIDERS] or list(DEFAULT_PROVIDER_ORDER)

    def set_provider_order(self, order: list[str]) -> list[str]:
        cleaned = [p for p in order if p in DATA_PROVIDERS]
        self.set(KEY_PROVIDER_ORDER, cleaned)
        return cleaned

    # ---- AI provider selection (Phase 6) ----------------------------------
    def get_active_ai_provider(self) -> str:
        provider = self.get(KEY_ACTIVE_AI_PROVIDER)
        if provider in AI_PROVIDERS:
            return provider
        return DEFAULT_AI_PROVIDER

    def set_active_ai_provider(self, provider: str) -> str:
        if provider not in AI_PROVIDERS:
            raise ValueError(f"Unknown AI provider: {provider}")
        self.set(KEY_ACTIVE_AI_PROVIDER, provider)
        return provider

    def get_ai_model(self) -> str | None:
        """An optional model override for the active provider (else its default)."""
        model = self.get(KEY_AI_MODEL)
        return model if isinstance(model, str) and model.strip() else None

    def set_ai_model(self, model: str | None) -> str | None:
        self.set(KEY_AI_MODEL, model)
        return model


class SecretsService:
    def __init__(self) -> None:
        self._box = get_secret_box()

    def set(self, provider: str, api_key: str) -> None:
        if provider not in KNOWN_PROVIDERS:
            raise ValueError(f"Unknown provider: {provider}")
        ciphertext = self._box.encrypt(api_key.strip())
        with session_scope() as s:
            row = s.get(SecretRow, provider)
            if row is None:
                s.add(SecretRow(provider=provider, ciphertext=ciphertext))
            else:
                row.ciphertext = ciphertext

    def get(self, provider: str) -> str | None:
        """Engine-internal only — returns the decrypted key. Never expose via API."""
        with session_scope() as s:
            row = s.get(SecretRow, provider)
            if row is None:
                return None
            return self._box.decrypt(row.ciphertext)

    def delete(self, provider: str) -> bool:
        with session_scope() as s:
            row = s.get(SecretRow, provider)
            if row is None:
                return False
            s.delete(row)
            return True

    def is_configured(self, provider: str) -> bool:
        with session_scope() as s:
            return s.get(SecretRow, provider) is not None

    def status(self) -> dict[str, bool]:
        with session_scope() as s:
            configured = {r.provider for r in s.query(SecretRow.provider).all()}
        return {p: (p in configured) for p in KNOWN_PROVIDERS}
