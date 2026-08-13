"""Google Gemini provider using the supported ``google-genai`` SDK."""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.ai.base import ProviderError

DEFAULT_MODEL = "gemini-2.5-flash"

_MODEL_ALIASES: dict[str, str] = {
    "gemini": DEFAULT_MODEL,
    "gemini-pro": "gemini-2.5-pro",
    "gemini-1.5-flash": DEFAULT_MODEL,
    "gemini-1.5-flash-latest": DEFAULT_MODEL,
    "gemini-1.5-pro": "gemini-2.5-pro",
    "gemini-1.5-pro-latest": "gemini-2.5-pro",
}


def resolve_gemini_model(model: str | None) -> str:
    """Map blank, alias, and deprecated names onto a current model id."""
    if not model or not str(model).strip():
        return DEFAULT_MODEL
    key = str(model).strip()
    if key.startswith("models/"):
        key = key[len("models/") :]
    return _MODEL_ALIASES.get(key, key)


def _to_contents(messages: list[dict[str, str]]) -> list[dict[str, object]]:
    """Map chat messages to Gemini's user/model roles."""
    contents: list[dict[str, object]] = []
    for message in messages:
        role = "model" if message["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": message["content"]}]})
    return contents


def _config(system: str | None, max_tokens: int) -> dict[str, object]:
    config: dict[str, object] = {"max_output_tokens": max_tokens}
    if system:
        config["system_instruction"] = system
    return config


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str | None = None) -> None:
        try:
            from google import genai
        except ImportError as exc:  # pragma: no cover - optional dep
            raise ProviderError(
                "The 'google-genai' package is not installed. Run "
                "`pip install google-genai`."
            ) from exc
        self.model = resolve_gemini_model(model)
        self._client = genai.Client(api_key=api_key)

    async def complete(
        self, system: str, prompt: str, *, max_tokens: int = 2048
    ) -> str:
        try:
            response = await self._client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
                config=_config(system, max_tokens),
            )
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(str(exc)) from exc
        return response.text or ""

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        system: str | None = None,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        try:
            response = await self._client.aio.models.generate_content_stream(
                model=self.model,
                contents=_to_contents(messages),
                config=_config(system, max_tokens),
            )
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(str(exc)) from exc

    async def aclose(self) -> None:
        await self._client.aio.aclose()
