"""OpenAI provider (optional). Uses the official async ``openai`` SDK, imported
lazily so it is only required when OpenAI is the active provider."""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.ai.base import ProviderError

DEFAULT_MODEL = "gpt-4o"


class OpenAIProvider:
    name = "openai"

    def __init__(self, api_key: str, model: str | None = None) -> None:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:  # pragma: no cover - optional dep
            raise ProviderError(
                "The 'openai' package is not installed. Run `pip install openai`."
            ) from exc
        self.model = model or DEFAULT_MODEL
        self._client = AsyncOpenAI(api_key=api_key)

    async def complete(
        self, system: str, prompt: str, *, max_tokens: int = 2048
    ) -> str:
        try:
            resp = await self._client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            )
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(str(exc)) from exc
        return resp.choices[0].message.content or ""

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        system: str | None = None,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        full = ([{"role": "system", "content": system}] if system else []) + messages
        try:
            stream = await self._client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=full,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(str(exc)) from exc

    async def aclose(self) -> None:
        await self._client.close()
