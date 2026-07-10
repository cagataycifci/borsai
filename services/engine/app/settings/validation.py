"""Live API-key verification for configured providers.

Each verifier performs a minimal, low-cost remote call (or local probe for
Ollama) and returns ``(ok, message)``. Used by the secrets API "test" route
and by the ``scripts/verify-keys.py`` smoke helper.
"""

from __future__ import annotations

import httpx

from app.settings.service import AI_PROVIDERS, DATA_PROVIDERS, KNOWN_PROVIDERS

_FINNHUB_BASE = "https://finnhub.io/api/v1"
_OLLAMA_TAGS = "http://127.0.0.1:11434/api/tags"


async def verify_provider_key(provider: str, api_key: str | None = None) -> tuple[bool, str]:
    """Verify a provider key. Keyless providers always succeed."""
    if provider not in KNOWN_PROVIDERS:
        return False, f"Unknown provider: {provider}"

    if not KNOWN_PROVIDERS[provider]:
        if provider == "ollama":
            return await _verify_ollama()
        return True, f"{provider} does not require an API key"

    if not api_key or not api_key.strip():
        return False, "No API key provided"

    key = api_key.strip()
    if provider == "finnhub":
        return await _verify_finnhub(key)
    if provider == "anthropic":
        return await _verify_anthropic(key)
    if provider == "openai":
        return await _verify_openai(key)
    if provider == "gemini":
        return await _verify_gemini(key)
    return False, f"No verifier for provider: {provider}"


async def _verify_finnhub(api_key: str) -> tuple[bool, str]:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{_FINNHUB_BASE}/quote",
            params={"symbol": "AAPL"},
            headers={"X-Finnhub-Token": api_key},
        )
        if resp.status_code in (401, 403):
            return False, "Invalid Finnhub API key"
        if resp.status_code == 429:
            return True, "Finnhub key accepted (rate limited)"
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            return False, f"Finnhub error: {exc.response.status_code}"
        data = resp.json()
        if data.get("c") is None:
            return False, "Finnhub returned an empty quote — key may be invalid"
        return True, "Finnhub key verified"


async def _verify_anthropic(api_key: str) -> tuple[bool, str]:
    try:
        from anthropic import AsyncAnthropic
    except ImportError:
        return False, "anthropic package not installed in engine venv"
    try:
        client = AsyncAnthropic(api_key=api_key)
        await client.models.list(limit=1)
        return True, "Anthropic key verified"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


async def _verify_openai(api_key: str) -> tuple[bool, str]:
    try:
        from openai import AsyncOpenAI
    except ImportError:
        return False, "openai package not installed in engine venv"
    try:
        client = AsyncOpenAI(api_key=api_key)
        await client.models.list(limit=1)
        return True, "OpenAI key verified"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


async def _verify_gemini(api_key: str) -> tuple[bool, str]:
    import asyncio

    try:
        import google.generativeai as genai
    except ImportError:
        return False, "google-generativeai package not installed in engine venv"
    try:
        genai.configure(api_key=api_key)
        models = await asyncio.to_thread(lambda: list(genai.list_models()))
        if not models:
            return False, "Gemini returned no models — key may be invalid"
        return True, "Gemini key verified"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


async def _verify_ollama() -> tuple[bool, str]:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(_OLLAMA_TAGS)
            resp.raise_for_status()
            models = resp.json().get("models", [])
        if not models:
            return False, "Ollama is running but no models are installed"
        return True, f"Ollama reachable ({len(models)} model(s))"
    except Exception as exc:  # noqa: BLE001
        return False, f"Ollama not reachable at {_OLLAMA_TAGS}: {exc}"


def providers_requiring_key() -> list[str]:
    return [p for p, needs in {**DATA_PROVIDERS, **AI_PROVIDERS}.items() if needs]
