import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from triage_app.api.routes import router as api_router

# Load environment variables
load_dotenv()

app = FastAPI(title="Bug Triage Engine")

# Configure CORS
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
if "*" not in origins:
    origins.append("*")  # Fallback for development flexibility

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

# WebSocket Endpoint
from fastapi import WebSocket, WebSocketDisconnect
from triage_app.socket_manager import manager

@app.websocket("/ws/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    await manager.connect(websocket, run_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, run_id)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("TRIAGE_ENGINE_PORT", 8004))
    host = os.getenv("TRIAGE_ENGINE_HOST", "127.0.0.1")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False
    )


