import asyncio
import logging

from fastapi import WebSocket

log = logging.getLogger(__name__)


class EventBus:
    def __init__(self):
        self.clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def register(self, websocket: WebSocket) -> None:
        async with self._lock:
            self.clients.add(websocket)

    async def unregister(self, websocket: WebSocket) -> None:
        async with self._lock:
            self.clients.discard(websocket)

    async def broadcast(self, message: dict) -> None:
        if not self.clients:
            return
        dead: list[WebSocket] = []
        for client in list(self.clients):
            try:
                await asyncio.wait_for(client.send_json(message), timeout=2)
            except Exception:  # noqa: BLE001 - a dead client must never break a job
                dead.append(client)
        for client in dead:
            await self.unregister(client)
