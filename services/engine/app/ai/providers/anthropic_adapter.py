"""Anthropic (Claude) provider — the reference AI adapter.

Uses the official ``anthropic`` async SDK. Defaults to the latest Claude model
(``claude-opus-4-8``). Thinking is intentionally left off here: analysis and chat
want predictable, low-latency, text-only output for the terminal, so we stream
plain text deltas rather than summarized reasoning blocks.

The SDK is imported lazily so the engine (and the test suite, which uses a fake
provider) does not require ``anthropic`` to be installed unless Claude is the
active provider.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.ai.base import ProviderError
from app.core.logging import get_logger

logger = get_logger(__name__)

DEFAULT_MODEL = "claude-opus-4-8"


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str, model: str | None = None) -> None:
        try:
            from anthropic import AsyncAnthropic
        except ImportError as exc:  # pragma: no cover - depends on optional dep
            raise ProviderError(
                "The 'anthropic' package is not installed. Run "
                "`pip install anthropic` in the engine venv."
            ) from exc
        self.model = model or DEFAULT_MODEL
        self._client = AsyncAnthropic(api_key=api_key)

    async def complete(
        self, system: str, prompt: str, *, max_tokens: int = 2048
    ) -> str:
        try:
            message = await self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:  # noqa: BLE001 - surface a uniform provider error
            raise ProviderError(str(exc)) from exc
        return "".join(
            block.text for block in message.content if block.type == "text"
        )

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        system: str | None = None,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        kwargs: dict[str, object] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        try:
            async with self._client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(str(exc)) from exc

    async def aclose(self) -> None:
        await self._client.close()
