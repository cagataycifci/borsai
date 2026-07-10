"""Request/response schemas for the watchlists API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Watchlist(BaseModel):
    id: int
    name: str
    position: int
    symbols: list[str]  # ordered symbols (convenience for the renderer)


class WatchlistCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class WatchlistUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class WatchlistItemCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)


class WatchlistReorder(BaseModel):
    symbols: list[str] = Field(description="Symbols in the desired order")
