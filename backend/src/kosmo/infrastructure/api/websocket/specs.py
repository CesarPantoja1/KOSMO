from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from kosmo.contracts.sdd.events import PipelineEvent

specs_ws_router = APIRouter()

_connections: dict[str, list[WebSocket]] = {}


async def broadcast_event(spec_id: str, event: PipelineEvent) -> None:
    sockets = _connections.get(spec_id, [])
    disconnected: list[WebSocket] = []
    for ws in sockets:
        try:
            await ws.send_json(event.model_dump(mode="json"))
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        sockets.remove(ws)


@specs_ws_router.websocket("/api/v1/specs/{spec_id}/events")
async def spec_events(websocket: WebSocket, spec_id: str) -> None:
    await websocket.accept()
    if spec_id not in _connections:
        _connections[spec_id] = []
    _connections[spec_id].append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        _connections[spec_id].remove(websocket)
