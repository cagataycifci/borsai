"""WebSocket streaming hub.

Phase 1 implements realtime *quote* streaming: a client subscribes to a set of
symbols and the server pushes quote frames on an interval (data is delayed at the
free tier, so we poll the cache-backed service rather than a true push feed).

The same hub will later multiplex news and alert frames (Phases 5/7), all tagged
by a ``type`` discriminator so the renderer can route them.

Client → server messages:
    {"action": "subscribe",   "symbols": ["AAPL", "ASELS.IS"]}
    {"action": "unsubscribe", "symbols": ["AAPL"]}
    {"action": "ping"}

Server → client frames:
    {"type": "quote",  "data": <Quote>}
    {"type": "alert",  "data": <AlertEvent>}   # pushed by the alert monitor (Phase 7)
    {"type": "pong"}
    {"type": "error",  "message": "..."}

Each connection also registers with the app's :class:`ConnectionHub` so the
background alert monitor can broadcast fired-alert frames to every client,
independent of that client's quote subscription.
"""

from __future__ import annotations

import asyncio
import contextlib

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.logging import get_logger
from app.data.service import MarketDataService

logger = get_logger(__name__)

ws_router = APIRouter()

# How often to push quote frames for subscribed symbols.
STREAM_INTERVAL_SECONDS = 5.0


class StreamSession:
    """Per-connection state: tracked symbols + the push loop."""

    def __init__(self, websocket: WebSocket, service: MarketDataService) -> None:
        self._ws = websocket
        self._service = service
        self._symbols: set[str] = set()
        self._lock = asyncio.Lock()

    async def update_subscription(self, symbols: list[str], add: bool) -> None:
        async with self._lock:
            normalized = {MarketDataService.normalize(s) for s in symbols if s}
            if add:
                self._symbols |= normalized
            else:
                self._symbols -= normalized

    async def push_loop(self) -> None:
        """Periodically fetch and push quotes for the subscribed symbols."""
        while True:
            async with self._lock:
                symbols = list(self._symbols)
            for symbol in symbols:
                quote = await self._service.get_quote(symbol)
                if quote is not None:
                    await self._ws.send_json(
                        {"type": "quote", "data": quote.model_dump(mode="json")}
                    )
            await asyncio.sleep(STREAM_INTERVAL_SECONDS)


@ws_router.websocket("/ws/stream")
async def stream(websocket: WebSocket) -> None:
    await websocket.accept()
    service: MarketDataService = websocket.app.state.market_data
    hub = getattr(websocket.app.state, "ws_hub", None)
    session = StreamSession(websocket, service)

    if hub is not None:
        hub.add(websocket)
    pusher = asyncio.create_task(session.push_loop())
    try:
        while True:
            message = await websocket.receive_json()
            action = message.get("action")
            if action == "subscribe":
                await session.update_subscription(message.get("symbols", []), add=True)
            elif action == "unsubscribe":
                await session.update_subscription(message.get("symbols", []), add=False)
            elif action == "ping":
                await websocket.send_json({"type": "pong"})
            else:
                await websocket.send_json(
                    {"type": "error", "message": f"unknown action: {action!r}"}
                )
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as exc:  # noqa: BLE001
        logger.warning("WebSocket error: %s", exc)
    finally:
        if hub is not None:
            hub.remove(websocket)
        pusher.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await pusher
