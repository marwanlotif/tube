import asyncio
import hmac

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.security import origin_allowed
from app.schemas.serialize import download_out

router = APIRouter(tags=["events"])


@router.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    state = websocket.app.state
    origin = websocket.headers.get("origin")
    host = websocket.headers.get("host", "")
    if not origin_allowed(origin, host, state.config):
        await websocket.close(code=4403)
        return

    await websocket.accept()
    try:
        message = await asyncio.wait_for(websocket.receive_json(), timeout=3)
    except (TimeoutError, WebSocketDisconnect, ValueError):
        await websocket.close(code=4401)
        return
    supplied = str(message.get("token") or "") if isinstance(message, dict) else ""
    if message.get("type") != "auth" or not hmac.compare_digest(supplied, state.token):
        await websocket.close(code=4401)
        return

    await state.events.register(websocket)
    try:
        rows = await state.repo.list_rows(limit=100)
        await websocket.send_json(
            {"type": "snapshot", "downloads": [download_out(row) for row in rows]}
        )
        while True:
            incoming = await websocket.receive_json()
            if isinstance(incoming, dict) and incoming.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        await state.events.unregister(websocket)
