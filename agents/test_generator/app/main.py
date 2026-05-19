"""FastAPI application main entry point."""
print("\n--- SERVER UPDATED BY AGENT ---")
print("\n--- SERVER INITIALIZING ---\n")
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Dict, List
import asyncio
import json
from app.core.config import settings
from app.core.logger import app_logger
from app.routers import testgen
from app.models.schemas import ErrorResponse
import uvicorn


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown."""
    # Startup
    app_logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    # Get and display server URLs
    import socket
    try:
        # Get local IP address
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        # Try to get actual network IP (not 127.0.0.1)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        network_ip = s.getsockname()[0]
        s.close()
        
        app_logger.info("=" * 50)
        app_logger.info("Server URLs:")
        app_logger.info(f"  Local:    http://localhost:8001")
        app_logger.info(f"  Local:    http://127.0.0.1:8001")
        app_logger.info(f"  Network:  http://{network_ip}:8001")
        app_logger.info(f"  Frontend: http://{network_ip}:8001/frontend")
        app_logger.info(f"  Swagger:  http://{network_ip}:8001/docs")
        app_logger.info("=" * 50)
    except Exception:
        # Fallback if IP detection fails
        app_logger.info("Server running on http://0.0.0.0:8001")
        app_logger.info("Swagger UI: http://localhost:8001/docs")
    
    app_logger.info("Application startup complete")
    yield
    # Shutdown
    app_logger.info("Application shutdown")


# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Backend service for generating test cases from software requirements using LLM",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    servers=[
        {"url": "http://localhost:8001", "description": "Local development server"},
        {"url": "http://127.0.0.1:8001", "description": "Local server (alternative)"},
    ],
)


# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods_list,
    allow_headers=settings.cors_allow_headers_list,
)


# Include routers
app.include_router(testgen.router)

# Store job queues for WebSocket
job_queues: Dict[str, asyncio.Queue] = {}

@app.websocket("/ws/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    await websocket.accept()
    app_logger.info(f"WebSocket connection established for job: {run_id}")
    
    # 1. Check if there is a recorded state for this job
    from app.routers.testgen import jobs
    job_data = jobs.get(run_id)
    if job_data:
        status = job_data.get("status")
        if status in ["completed", "failed"]:
            # If already completed or failed, send the final state immediately
            event_type = "completed" if status == "completed" else "error"
            ws_message = {
                "event": event_type,
                "agent": "test_generator",
                "status": status,
                "percent": job_data.get("percent", 100),
                "metrics": job_data.get("metrics"),
                "error": job_data.get("error"),
                "message": job_data.get("error") or job_data.get("message")
            }
            await websocket.send_json(ws_message)
            app_logger.info(f"WebSocket: Job {run_id} is already {status}. Sending final state and keeping alive.")
            try:
                while True:
                    await websocket.receive_text()
            except WebSocketDisconnect:
                pass
            return

    # 2. Otherwise, fall back to real-time subscription
    from app.utils.sse_manager import sse_manager
    queue = await sse_manager.connect()
    
    try:
        # Send initial "running" status if we know it's running
        if job_data and job_data.get("status") == "running":
            await websocket.send_json({
                "event": "progress",
                "agent": "test_generator",
                "status": "running",
                "percent": job_data.get("percent", 10)
            })

        while True:
            # Receive from SSE manager and send to WebSocket
            message_json = await queue.get()
            message = json.loads(message_json)
            
            # Map SSE format (type/data) to Dashboard format (event/payload)
            ws_message = {
                "event": message.get("type"),
                "payload": message.get("data"),
                "agent": "test_generator"
            }
            # Also support flat format if needed
            ws_message.update(message.get("data", {}))
            
            await websocket.send_json(ws_message)
            
            if ws_message.get("event") == "completed" or ws_message.get("status") == "completed":
                # Keep alive so frontend hook is happy during handover
                app_logger.info(f"WebSocket: Job {run_id} transitioned to completed. Keeping alive.")
                try:
                    while True:
                        await websocket.receive_text()
                except WebSocketDisconnect:
                    break
    except WebSocketDisconnect:
        app_logger.info(f"WebSocket disconnected for job: {run_id}")
    except Exception as e:
        app_logger.error(f"WebSocket error: {str(e)}")
    finally:
        await sse_manager.disconnect(queue)
        try:
            from starlette.websockets import WebSocketState
            if websocket.client_state != WebSocketState.DISCONNECTED:
                await websocket.close()
        except Exception:
            pass

# Serve frontend static files
import os
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    # Serve index.html at /frontend
    @app.get("/frontend", tags=["frontend"])
    async def serve_frontend():
        """Serve frontend index.html."""
        index_path = os.path.join(frontend_path, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return JSONResponse({"error": "Frontend not found"}, status_code=404)
    
    # Serve static files (CSS, JS, images, etc.)
    app.mount("/frontend/", StaticFiles(directory=frontend_path), name="frontend_static")


# Global exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    app_logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        ).model_dump()
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle ValueError exceptions."""
    app_logger.warning(f"ValueError: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            error="Invalid input",
            detail=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST
        ).model_dump()
    )


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs",
        "frontend": "/frontend"
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8001,
        reload=settings.debug,
        log_level="info"
    )
