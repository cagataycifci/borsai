from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import pytest

from app.ai.providers.gemini_adapter import GeminiProvider, resolve_gemini_model


class _Stream:
    def __aiter__(self):
        async def chunks():
            yield SimpleNamespace(text="first")
            yield SimpleNamespace(text="")
            yield SimpleNamespace(text=" second")

        return chunks()


class _Models:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def generate_content(self, **kwargs):
        self.calls.append(("complete", kwargs))
        return SimpleNamespace(text="answer")

    async def generate_content_stream(self, **kwargs):
        self.calls.append(("stream", kwargs))
        return _Stream()


class _AsyncClient:
    def __init__(self) -> None:
        self.models = _Models()
        self.closed = False

    async def aclose(self) -> None:
        self.closed = True


class _Client:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.aio = _AsyncClient()


def _install_fake_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    google = ModuleType("google")
    genai = ModuleType("google.genai")
    genai.Client = _Client  # type: ignore[attr-defined]
    google.genai = genai  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "google", google)
    monkeypatch.setitem(sys.modules, "google.genai", genai)


def test_resolve_gemini_model_aliases() -> None:
    assert resolve_gemini_model(None) == "gemini-2.5-flash"
    assert resolve_gemini_model("models/gemini-1.5-pro") == "gemini-2.5-pro"
    assert resolve_gemini_model("gemini-custom") == "gemini-custom"


@pytest.mark.asyncio
async def test_gemini_provider_uses_supported_async_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_sdk(monkeypatch)
    provider = GeminiProvider("test-key", "gemini")

    assert await provider.complete("system", "prompt", max_tokens=123) == "answer"
    assert [part async for part in provider.stream(
        [{"role": "user", "content": "hello"}], system="system", max_tokens=99
    )] == ["first", " second"]

    calls = provider._client.aio.models.calls
    assert calls[0][1]["model"] == "gemini-2.5-flash"
    assert calls[0][1]["config"] == {
        "max_output_tokens": 123,
        "system_instruction": "system",
    }
    assert calls[1][1]["contents"] == [
        {"role": "user", "parts": [{"text": "hello"}]}
    ]

    await provider.aclose()
    assert provider._client.aio.closed is True
