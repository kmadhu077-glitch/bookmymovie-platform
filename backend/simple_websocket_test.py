"""
Simple WebSocket Test Service - Minimal implementation to verify WebSocket functionality
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio

app = FastAPI(title="Simple WebSocket Test")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple connection manager
class SimpleConnectionManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"Client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"Client disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove broken connections
                self.active_connections.remove(connection)

manager = SimpleConnectionManager()

@app.get("/")
async def root():
    return {"message": "Simple WebSocket Test Service", "status": "running"}

@app.websocket("/ws/test")
async def websocket_endpoint(websocket: WebSocket):
    """Simple WebSocket test endpoint"""
    await manager.connect(websocket)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            print(f"Received: {message}")
            
            # Echo back the message
            response = {
                "type": "echo",
                "original_message": message,
                "timestamp": "2025-10-16 15:42:00",
                "connections": len(manager.active_connections)
            }
            
            await manager.send_personal_message(json.dumps(response), websocket)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.websocket("/ws/seats/{showtime_id}")
async def websocket_seats_simple(websocket: WebSocket, showtime_id: int):
    """Simple seat updates endpoint"""
    await manager.connect(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            print(f"Seat message for showtime {showtime_id}: {message}")
            
            # Simple seat response
            response = {
                "type": "seat_selection",
                "showtime_id": showtime_id,
                "action": message.get("action", "unknown"),
                "seats": message.get("seats", []),
                "session_id": message.get("session_id", "unknown")
            }
            
            await manager.send_personal_message(json.dumps(response), websocket)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    print("Starting Simple WebSocket Test Service on port 8009")
    uvicorn.run(app, host="127.0.0.1", port=8009)