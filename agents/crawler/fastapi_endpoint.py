import asyncio
import websockets # Force check for websocket support
from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Header
from typing import Dict, List, Optional
import os
import logging
from config import CrawlerConfig
from qa_garden_crawler import QAGardenCrawler
from fastapi.middleware.cors import CORSMiddleware

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fastapi_endpoint")

app = FastAPI(title="QA Garden Phase-1 Crawler API")

# Enable CORS for the Dashboard (Next.js)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for local dev, or specify ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple API Key Security (Load from .env in prod)
API_KEY = os.getenv("QA_GARDEN_API_KEY", "qa-garden-secret-key")

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

# Store active jobs, their progress queues, and crawler instances
jobs: Dict[str, Dict] = {}
job_queues: Dict[str, asyncio.Queue] = {}
job_instances: Dict[str, QAGardenCrawler] = {}

@app.get("/")
def read_root():
    return {"message": "QA Garden Crawler API is running."}

@app.post("/crawl")
async def start_crawl(config: CrawlerConfig, background_tasks: BackgroundTasks, x_api_key: str = Header(...)):
    """
    Trigger a new crawl job. Requires X-API-Key header.
    """
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
        
    run_id = f"job_{len(jobs) + 1}"
    config.job_id = run_id # Sync job ID
    
    jobs[run_id] = {"status": "starting", "config": config.dict()}
    job_queues[run_id] = asyncio.Queue()
    
    # Add to background tasks
    background_tasks.add_task(run_crawler_task, run_id, config)
    
    return {
        "run_id": run_id, # Changed from job_id to match frontend
        "status": "accepted",
        "message": "Crawl job started in background.",
        "locators_url": f"/job/{run_id}",
        "ws_url": f"/ws/{run_id}"
    }

@app.post("/pause/{run_id}")
async def pause_run(run_id: str):
    if run_id not in job_instances:
        raise HTTPException(status_code=404, detail="Active run not found")
    job_instances[run_id].pause_event.clear()
    return {"status": "paused", "run_id": run_id}

@app.post("/resume/{run_id}")
async def resume_run(run_id: str):
    if run_id not in job_instances:
        raise HTTPException(status_code=404, detail="Active run not found")
    job_instances[run_id].pause_event.set()
    return {"status": "resumed", "run_id": run_id}

@app.post("/abort/{run_id}")
async def abort_run(run_id: str):
    if run_id not in job_instances:
        raise HTTPException(status_code=404, detail="Active run not found")
    job_instances[run_id].abort_event.set()
    # Also resume it if it was paused to let it exit
    job_instances[run_id].pause_event.set()
    return {"status": "aborting", "run_id": run_id}

@app.get("/job/{run_id}")
async def get_job_status(run_id: str):
    if run_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[run_id]

from starlette.websockets import WebSocketState

@app.websocket("/ws/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    await websocket.accept()
    logger.info(f"WebSocket connection attempt for job: {run_id}")
    
    # If the job is already finished, send a final update and keep connection alive
    if run_id in jobs and jobs[run_id]["status"] in ["completed", "failed"]:
        logger.info(f"WebSocket: Job {run_id} already {jobs[run_id]['status']}. Sending final update.")
        await websocket.send_json(jobs[run_id].get("result") or {"status": jobs[run_id]["status"], "event": "completed", "agent": "crawler"})
        try:
            # Wait for client to disconnect
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            logger.info(f"WebSocket closed by client for finished job: {run_id}")
        return

    if run_id not in job_queues:
        logger.warning(f"WebSocket rejected: Job {run_id} not found in active queues.")
        await websocket.send_json({"event": "error", "message": f"Job {run_id} not found or expired. Please start a new run."})
        await websocket.close()
        return

    logger.info(f"WebSocket connected for job: {run_id}")
    try:
        while True:
            # Get next update from the job's queue
            update = await job_queues[run_id].get()
            await websocket.send_json(update)
            
            if update.get("status") in ["completed", "failed"]:
                # Don't break! Keep alive so frontend hook is happy during handover
                logger.info(f"WebSocket: Job {run_id} transitioned to {update.get('status')}. Keeping alive.")
                while True:
                    await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for job: {run_id}")
    except Exception as e:
        logger.error(f"WebSocket error for job {run_id}: {e}")
    finally:
        if websocket.client_state != WebSocketState.DISCONNECTED:
            try:
                await websocket.close()
            except:
                pass

async def run_crawler_task(run_id: str, config: CrawlerConfig):
    try:
        crawler = QAGardenCrawler(config)
        job_instances[run_id] = crawler # Store instance for control
        jobs[run_id]["status"] = "in_progress"
        
        # We iterate through the generator to get updates
        first_update = True
        async for update in crawler.run():
            # Inject metrics and config into the progress update for the dashboard
            if update.get("event") == "progress":
                update["metrics"] = {
                    "elements": len(crawler.all_locators),
                    "discovered": len(crawler.discovered_urls),
                    "finished": len(crawler.finished_urls),
                    "depth": update.get("depth", 0),
                    "url": update.get("url", ""),
                    "coverage": round((len(crawler.finished_urls) / len(crawler.discovered_urls) * 100), 2) if crawler.discovered_urls else 0
                }
                if first_update:
                    update["config"] = jobs[run_id]["config"]
                    first_update = False

            jobs[run_id]["last_update"] = update
            
            # Put update into queue for WebSocket subscribers
            if run_id in job_queues:
                await job_queues[run_id].put(update)
            
            if update.get("status") == "completed":
                # Inject correct path
                if hasattr(crawler, 'locators_dir'):
                    abs_path = os.path.abspath(crawler.locators_dir)
                    update["path"] = abs_path
                    logger.info(f"Injecting absolute path into completion: {abs_path}")

                jobs[run_id]["status"] = "completed"
                jobs[run_id]["result"] = update
                
    except Exception as e:
        logger.error(f"Crawler job {run_id} failed: {e}")
        jobs[run_id]["status"] = "failed"
        jobs[run_id]["error"] = str(e)
        if run_id in job_queues:
            await job_queues[run_id].put({"status": "failed", "event": "completed", "error": str(e)})
    finally:
        # Final safety check: if we didn't send a completed/failed status, send one now
        if jobs.get(run_id, {}).get("status") not in ["completed", "failed"]:
            status = "completed" # Assume completed if reached end without exception
            final_msg = {
                "status": status, 
                "event": "completed", 
                "agent": "crawler", 
                "message": "Task ended."
            }
            # Include locators path for handover (use absolute path)
            if 'crawler' in locals() and hasattr(crawler, 'locators_dir'):
                abs_path = os.path.abspath(crawler.locators_dir)
                final_msg["path"] = abs_path
                logger.info(f"Injecting path into completion: {abs_path}")
                
            if run_id in job_queues:
                await job_queues[run_id].put(final_msg)
        
        if run_id in job_instances:
            del job_instances[run_id]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8005)

