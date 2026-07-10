"""Tests for the TTL cache."""

from __future__ import annotations

import asyncio

import pytest

from app.core.cache import TTLCache


async def test_get_or_set_computes_once() -> None:
    cache: TTLCache[int] = TTLCache(ttl=60)
    calls = 0

    async def factory() -> int:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
        return 42

    a = await cache.get_or_set("k", factory)
    b = await cache.get_or_set("k", factory)

    assert a == b == 42
    assert calls == 1  # second call served from cache


async def test_expiry() -> None:
    cache: TTLCache[str] = TTLCache(ttl=0.01)
    cache.set("k", "v")
    assert cache.get("k") == "v"
    await asyncio.sleep(0.02)
    assert cache.get("k") is None


async def test_concurrent_calls_dedupe() -> None:
    cache: TTLCache[int] = TTLCache(ttl=60)
    calls = 0

    async def factory() -> int:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.01)
        return 7

    results = await asyncio.gather(*(cache.get_or_set("k", factory) for _ in range(10)))
    assert results == [7] * 10
    assert calls == 1
