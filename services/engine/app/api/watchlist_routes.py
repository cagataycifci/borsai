"""Watchlist CRUD API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.watchlists import (
    Watchlist,
    WatchlistCreate,
    WatchlistItemCreate,
    WatchlistReorder,
    WatchlistService,
    WatchlistUpdate,
)

from .deps import get_watchlist_service

router = APIRouter(prefix="/api/v1/watchlists", tags=["watchlists"])

WatchlistDep = Annotated[WatchlistService, Depends(get_watchlist_service)]


def _require(watchlist: Watchlist | None, watchlist_id: int) -> Watchlist:
    if watchlist is None:
        raise HTTPException(status_code=404, detail=f"No watchlist {watchlist_id}")
    return watchlist


@router.get("", response_model=list[Watchlist], summary="List watchlists")
def list_watchlists(service: WatchlistDep) -> list[Watchlist]:
    return service.list()


@router.post("", response_model=Watchlist, summary="Create a watchlist")
def create_watchlist(service: WatchlistDep, body: WatchlistCreate) -> Watchlist:
    return service.create(body.name)


@router.put("/{watchlist_id}", response_model=Watchlist, summary="Rename a watchlist")
def rename_watchlist(
    service: WatchlistDep, watchlist_id: int, body: WatchlistUpdate
) -> Watchlist:
    return _require(service.rename(watchlist_id, body.name), watchlist_id)


@router.delete("/{watchlist_id}", summary="Delete a watchlist")
def delete_watchlist(service: WatchlistDep, watchlist_id: int) -> dict[str, bool]:
    if not service.delete(watchlist_id):
        raise HTTPException(status_code=404, detail=f"No watchlist {watchlist_id}")
    return {"deleted": True}


@router.post(
    "/{watchlist_id}/items", response_model=Watchlist, summary="Add a symbol"
)
def add_item(
    service: WatchlistDep, watchlist_id: int, body: WatchlistItemCreate
) -> Watchlist:
    return _require(service.add_item(watchlist_id, body.symbol), watchlist_id)


@router.delete(
    "/{watchlist_id}/items/{symbol}", response_model=Watchlist, summary="Remove a symbol"
)
def remove_item(service: WatchlistDep, watchlist_id: int, symbol: str) -> Watchlist:
    return _require(service.remove_item(watchlist_id, symbol), watchlist_id)


@router.put(
    "/{watchlist_id}/items", response_model=Watchlist, summary="Reorder symbols"
)
def reorder_items(
    service: WatchlistDep, watchlist_id: int, body: WatchlistReorder
) -> Watchlist:
    return _require(service.reorder_items(watchlist_id, body.symbols), watchlist_id)
