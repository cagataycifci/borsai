"""Google Gemini provider (optional). Uses ``google-generativeai``, imported
lazily so it is only required when Gemini is the active provider."""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.ai.base import ProviderError

# gemini-1.5-* was shut down; use the current Flash workhorse.
DEFAULT_MODEL = "gemini-2.5-flash"

# Names users / the Settings UI accidentally persist as ``ai.model``.
_MODEL_ALIASES: dict[str, str] = {
    "gemini": DEFAULT_MODEL,
    "gemini-pro": "gemini-2.5-pro",
    "gemini-1.5-flash": DEFAULT_MODEL,
    "gemini-1.5-flash-latest": DEFAULT_MODEL,
    "gemini-1.5-pro": "gemini-2.5-pro",
    "gemini-1.5-pro-latest": "gemini-2.5-pro",
}


def resolve_gemini_model(model: str | None) -> str:
    """Map blank / alias / deprecated names onto a live Gemini model id."""
    if not model or not str(model).strip():
        return DEFAULT_MODEL
    key = str(model).strip()
    if key.startswith("models/"):
        key = key[len("models/") :]
    return _MODEL_ALIASES.get(key, key)


def _to_contents(messages: list[dict[str, str]]) -> list[dict[str, object]]:
    """Map chat messages (user/assistant) to Gemini's user/model roles."""
    contents: list[dict[str, object]] = []
    for m in messages:
        role = "model" if m["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [m["content"]]})
    return contents


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str | None = None) -> None:
        try:
            import google.generativeai as genai
        except ImportError as exc:  # pragma: no cover - optional dep
            raise ProviderError(
                "The 'google-generativeai' package is not installed. Run "
                "`pip install google-generativeai`."
            ) from exc
        genai.configure(api_key=api_key)
        self.model = resolve_gemini_model(model)
        self._genai = genai

    def _model(self, system: str | None):
        return self._genai.GenerativeModel(self.model, system_instruction=system or None)

    async def complete(
        self, system: str, prompt: str, *, max_tokens: int = 2048
    ) -> str:
        try:
            resp = await self._model(system).generate_content_async(
                prompt,
                generation_config={"max_output_tokens": max_tokens},
            )
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(str(exc)) from exc
        return resp.text or ""

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        system: str | None = None,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        try:
            resp = await self._model(system).generate_content_async(
                _to_contents(messages),
                generation_config={"max_output_tokens": max_tokens},
                stream=True,
            )
            async for chunk in resp:
                if chunk.text:
                    yield chunk.text
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(str(exc)) from exc

    async def aclose(self) -> None:
        return None
