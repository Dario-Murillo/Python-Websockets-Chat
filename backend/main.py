# main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import json
from datetime import datetime, timezone

app = FastAPI()

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

# Serve everything in /static at the /static URL path
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def get():
    return FileResponse("./static/index.html")

@app.websocket("/ws/{room_id}/{client_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, client_id: int):
    await manager.connect(websocket, room_id)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(f"You wrote: {data}", websocket)
            await manager.broadcast(json.dumps({
                "client_id": client_id,
                "room_id": room_id,
                "message": data,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), room_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
        await manager.broadcast(json.dumps({
            "client_id": client_id,
            "room_id": room_id,
            "message": "left the chat",
            "event": "disconnect",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), room_id)