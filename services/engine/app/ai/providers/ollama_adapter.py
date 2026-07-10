"""Ollama provider (optional, local). Talks to a local Ollama server over HTTP
(``httpx``), so it needs no API key — only a running ``ollama`` daemon."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from app.ai.base import ProviderError

DEFAULT_MODEL = "llama3.1"
DEFAULT_HOST = "http://127.0.0.1:11434"


class OllamaProvider:
    name = "ollama"

    def __init__(self, model: str | None = None, host: str = DEFAULT_HOST) -> None:
        self.model = model or DEFAULT_MODEL
        self._client = httpx.AsyncClient(base_url=host, timeout=120.0)

    async def complete(
        self, system: str, prompt: str, *, max_tokens: int = 2048
    ) -> str:
        try:
            resp = await self._client.post(
                "/api/chat",
                json={
                    "model": self.model,
                    "stream": False,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                },
            )
            resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(str(exc)) from exc
        return resp.json().get("message", {}).get("content", "")

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        system: str | None = None,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        full = ([{"role": "system", "content": system}] if system else []) + messages
        try:
            async with self._client.stream(
                "POST",
                "/api/chat",
                json={"model": self.model, "stream": True, "messages": full},
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    chunk = json.loads(line)
                    piece = chunk.get("message", {}).get("content", "")
                    if piece:
                        yield piece
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(str(exc)) from exc

    async def aclose(self) -> None:
        await self._client.aclose()
