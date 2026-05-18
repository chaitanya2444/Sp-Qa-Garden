
from fastapi import FastAPI
from triage_app.api.routes import router as api_router

app = FastAPI(title="Bug Triage Engine")

# All API routes will be under /api/...
app.include_router(api_router, prefix="/api")

from fastapi import WebSocket, WebSocketDisconnect
from triage_app.socket_manager import manager

@app.websocket("/ws/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    await manager.connect(websocket, run_id)
    
    # Check if there are already results for this run
    from triage_app.services import storage_service
    results = storage_service.get_results_by_run_id(run_id)
    
    # Check if there are already results or if the run is completed
    is_done = storage_service.is_run_completed(run_id)
    
    if is_done or results:
        await websocket.send_json({
            "event": "completed",
            "agent": "triage",
            "status": "completed",
            "percent": 100,
            "data": {"results": results}
        })
        
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, run_id)
