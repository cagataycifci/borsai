"""A minimal async-safe in-memory TTL cache.

Used to collapse duplicate requests and respect free-tier provider rate limits.
Deliberately dependency-free; can be swapped for Redis later behind the same API.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Generic, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    def __init__(self, ttl: float, maxsize: int = 4096) -> None:
        self._ttl = ttl
        self._maxsize = maxsize
        self._store: dict[str, tuple[float, T]] = {}
        self._lock = asyncio.Lock()

    def get(self, key: str) -> T | None:
        item = self._store.get(key)
        if item is None:
            return None
        expires_at, value = item
        if expires_at < time.monotonic():
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: T, ttl: float | None = None) -> None:
        if len(self._store) >= self._maxsize:
            # Drop the oldest-expiring entry (cheap, good enough for our sizes).
            oldest = min(self._store, key=lambda k: self._store[k][0])
            self._store.pop(oldest, None)
        self._store[key] = (time.monotonic() + (ttl or self._ttl), value)

    async def get_or_set(
        self, key: str, factory: Callable[[], Awaitable[T]], ttl: float | None = None
    ) -> T:
        """Return cached value, otherwise compute via ``factory`` under a lock."""
        cached = self.get(key)
        if cached is not None:
            return cached
        async with self._lock:
            # Re-check after acquiring the lock (another coroutine may have filled it).
            cached = self.get(key)
            if cached is not None:
                return cached
            value = await factory()
            self.set(key, value, ttl)
            return value

    def clear(self) -> None:
        self._store.clear()
