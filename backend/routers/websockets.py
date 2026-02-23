from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
from datetime import datetime, timezone

router = APIRouter(tags=["websocket"])

class ConnectionManager:
    def __init__(self):
        self._active_connections: dict[str, list[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, room_id: str):
        await websocket.accept()
        if room_id not in self._active_connections:
            self._active_connections[room_id] = []
        self._active_connections[room_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, room_id: str):
        self._active_connections[room_id].remove(websocket)

        if not self._active_connections[room_id]:
            del self._active_connections[room_id]
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str, room_id: str):
        connections = self._active_connections.get(room_id, [])
        for connection in connections:
            await connection.send_text(message)

manager = ConnectionManager()

@router.websocket("/ws/{room_id}/{client_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, client_id: int):
    await manager.connect(websocket, room_id)
    try:
        while True:
            rawData = await websocket.receive_text()
            data = json.loads(rawData)
            
            if data.get("type") == "join":
                await manager.broadcast(json.dumps({
                    "type": "join",
                    "username": data.get("username"),
                    "room_id": room_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }), room_id)
                continue

            await manager.send_personal_message(f"You wrote: {data}", websocket)
            await manager.broadcast(json.dumps({
                "type": "message",
                "client_id": client_id,
                "username": data.get("username"),
                "message": data.get("message"),
                "room_id": room_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), room_id)
            
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
        await manager.broadcast(json.dumps({
            "event": "disconnect",
            "username": "unknown",  # temporary until auth is added
            "room_id": room_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), room_id)