"""AI provider abstraction (Phase 6).

Mirrors the data-layer adapter pattern (:mod:`app.data.base`): a thin protocol
that concrete providers (Anthropic, OpenAI, Gemini, Ollama) implement, so the
:class:`~app.ai.service.AIService` and route handlers depend only on the
interface. Swapping or adding a provider is purely additive — register it in
:mod:`app.ai.factory`.

Providers expose two primitives:

* :meth:`complete` — a single non-streaming request returning the full text.
  Used for analysis and news classification (which then parse the text).
* :meth:`stream` — an async generator of text chunks. Used for chat.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable


class ProviderError(RuntimeError):
    """Raised when a provider cannot fulfil a request (auth, network, SDK)."""


@runtime_checkable
class AIProvider(Protocol):
    name: str
    model: str

    async def complete(
        self, system: str, prompt: str, *, max_tokens: int = 2048
    ) -> str:
        """Return the full completion text for a single prompt."""
        ...

    def stream(
        self,
        messages: list[dict[str, str]],
        *,
        system: str | None = None,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        """Yield completion text chunks for a chat-style message list."""
        ...

    async def aclose(self) -> None:
        """Release any underlying network client."""
        ...
