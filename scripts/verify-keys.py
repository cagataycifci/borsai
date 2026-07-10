#!/usr/bin/env python3
"""Smoke-test provider API keys from environment variables.

Reads optional keys from the environment and runs live verification:
  FINNHUB_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY / GOOGLE_API_KEY

Usage (from repo root, engine venv active):
  python scripts/verify-keys.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "services" / "engine"
sys.path.insert(0, str(ENGINE))

from app.settings.validation import providers_requiring_key, verify_provider_key  # noqa: E402

_ENV_MAP = {
    "finnhub": "FINNHUB_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
}


async def main() -> int:
    print("Borsa AI — live API key verification\n")
    failures = 0
    checked = 0

    for provider in providers_requiring_key():
        env_name = _ENV_MAP.get(provider, f"{provider.upper()}_API_KEY")
        key = os.environ.get(env_name) or os.environ.get("GOOGLE_API_KEY" if provider == "gemini" else "")
        if not key:
            print(f"  {provider:10} SKIP  (no {env_name})")
            continue
        checked += 1
        ok, message = await verify_provider_key(provider, key)
        status = "OK" if ok else "FAIL"
        print(f"  {provider:10} {status:4}  {message}")
        if not ok:
            failures += 1

    # Ollama is keyless but worth probing when present.
    ok, message = await verify_provider_key("ollama")
    print(f"  {'ollama':10} {'OK' if ok else 'SKIP':4}  {message}")

    print()
    if checked == 0:
        print("No API keys in environment — set FINNHUB_API_KEY etc. to run live checks.")
        return 0
    if failures:
        print(f"{failures} key(s) failed verification.")
        return 1
    print("All configured keys verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
