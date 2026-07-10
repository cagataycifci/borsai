"""Builds the active :class:`AIProvider` from the ``ai.active_provider`` setting
plus the encrypted secrets store — mirroring :mod:`app.data.factory`.

Returns ``None`` (rather than raising) when the selected provider needs a key
that isn't configured, so the service can report a "not ready" status instead of
erroring. Provider SDKs are imported lazily inside each adapter, so only the
active provider's dependency must be installed.
"""

from __future__ import annotations

from app.ai.base import AIProvider
from app.ai.providers import (
    AnthropicProvider,
    GeminiProvider,
    OllamaProvider,
    OpenAIProvider,
)
from app.core.logging import get_logger
from app.settings.service import AI_PROVIDERS, SecretsService, SettingsService

logger = get_logger(__name__)


def build_ai_provider(
    settings_service: SettingsService, secrets_service: SecretsService
) -> AIProvider | None:
    """Construct the configured AI provider, or ``None`` if not usable."""
    name = settings_service.get_active_ai_provider()
    model = settings_service.get_ai_model()
    needs_key = AI_PROVIDERS.get(name, True)

    key = secrets_service.get(name) if needs_key else None
    if needs_key and not key:
        logger.info("AI provider %s selected but no API key configured.", name)
        return None

    if name == "anthropic":
        return AnthropicProvider(key or "", model)
    if name == "openai":
        return OpenAIProvider(key or "", model)
    if name == "gemini":
        return GeminiProvider(key or "", model)
    if name == "ollama":
        return OllamaProvider(model)

    logger.warning("Unknown AI provider %s; no provider built.", name)
    return None
