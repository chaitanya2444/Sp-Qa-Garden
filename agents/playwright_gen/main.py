from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import subprocess
import json
import os
import sys
from pathlib import Path
import asyncio
from pydantic import BaseModel
from typing import Dict, List, Optional
import logging
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from starlette.websockets import WebSocketState
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="QA Garden UI/UX Test Automation API",
    description="API for managing Playwright test automation, test generation, and artifact management",
    version="1.0.0"
)

# Enable CORS for the Dashboard (Next.js)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent
TESTS_DIR = PROJECT_ROOT / "tests"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
SCREENSHOTS_DIR = ARTIFACTS_DIR / "screenshots"
VIDEOS_DIR = ARTIFACTS_DIR / "videos"
TEST_LOGS_DIR = ARTIFACTS_DIR / "logs"
TRACES_DIR = ARTIFACTS_DIR / "traces"
TESTCASES_DIR = PROJECT_ROOT / "testcases"
CONFIG_DIR = PROJECT_ROOT / "config"

# Create directories
ARTIFACTS_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
TEST_LOGS_DIR.mkdir(parents=True, exist_ok=True)
TRACES_DIR.mkdir(parents=True, exist_ok=True)
TESTCASES_DIR.mkdir(exist_ok=True)
CONFIG_DIR.mkdir(exist_ok=True)

# External API configuration
EXTERNAL_API_BASE_URL = os.getenv("EXTERNAL_API_BASE_URL")

# Mount static files
app.mount("/screenshots", StaticFiles(directory=str(SCREENSHOTS_DIR)), name="screenshots")
app.mount("/videos", StaticFiles(directory=str(VIDEOS_DIR)), name="videos")
app.mount("/logs", StaticFiles(directory=str(TEST_LOGS_DIR)), name="logs")

@app.get("/")
async def root():
    return {
        "message": "QA Garden UI/UX Test Automation API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "full_automation": "/automation/full/{page_type}",
            "test_execution": "/tests/run/{page_type}",
            "test_generation": "/generate/tests",
            "artifacts": "/artifacts/{page_type}",
            "test_cases": "/testcases/{page_type}",
            "test_results": "/results/{page_type}",
            "locators": "/config/locators/{page_type}",
            "available_pages": "/pages"
        }
    }

def get_available_pages() -> List[str]:
    """Dynamically discover available page types from local files"""
    pages = set()
    # Check testcases
    for f in TESTCASES_DIR.glob("*_testcases.json"):
        pages.add(f.stem.replace("_testcases", "").lower())
    # Check locators
    for f in CONFIG_DIR.glob("*_locators.json"):
        pages.add(f.stem.replace("_locators", "").lower())
    return sorted(list(pages))

@app.get("/pages")
async def list_pages():
    """List all dynamically detected page types"""
    return {"pages": get_available_pages()}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "project_root": str(PROJECT_ROOT)
    }

@app.get("/testcases/{page_type}")
async def get_testcases(page_type: str):
    """Get test cases from external API and save locally"""
    # Normalize input
    page_type = page_type.lower()
    available_pages = get_available_pages()
    
    # We allow the specific call if it's already in our local testcases even if not in "valid_pages"
    # But for safety we can still check against available ones if we want.
    
    try:
        # Try to fetch from external API first
        if EXTERNAL_API_BASE_URL:
            external_url = f"{EXTERNAL_API_BASE_URL}/testcases/{page_type}"
            
            response = requests.get(external_url, timeout=10)
            if response.status_code == 200:
                test_cases = response.json()
                
                # Save to local file as backup
                local_file = TESTCASES_DIR / f"{page_type}_testcases.json"
                with open(local_file, 'w', encoding='utf-8') as f:
                    json.dump(test_cases, f, indent=2)
                
                return test_cases
        
        # Fallback to local file
        local_file = TESTCASES_DIR / f"{page_type}_testcases.json"
        if local_file.exists():
            with open(local_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        raise HTTPException(status_code=404, detail=f"Test cases not found for {page_type}")
        
    except requests.exceptions.RequestException as e:
        # Fallback to local file on API error
        local_file = TESTCASES_DIR / f"{page_type}_testcases.json"
        if local_file.exists():
            with open(local_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        raise HTTPException(status_code=500, detail=f"Failed to fetch test cases: {str(e)}")

@app.get("/config/locators/{page_type}")
async def get_locators(page_type: str):
    """Get locators from external API and save as JSON file"""
    page_type = page_type.lower()
    
    try:
        # Try to fetch from external API first
        if EXTERNAL_API_BASE_URL:
            external_url = f"{EXTERNAL_API_BASE_URL}/config/locators/{page_type}"
            
            response = requests.get(external_url, timeout=10)
            if response.status_code == 200:
                locators_data = response.json()
                
                # Save to local JSON file
                local_file = CONFIG_DIR / f"{page_type}_locators.json"
                with open(local_file, 'w', encoding='utf-8') as f:
                    json.dump(locators_data, f, indent=2)
                
                return locators_data
        
        # Fallback to local file
        local_file = CONFIG_DIR / f"{page_type}_locators.json"
        if local_file.exists():
            with open(local_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        raise HTTPException(status_code=404, detail=f"Locators not found for {page_type}")
        
    except requests.exceptions.RequestException as e:
        # Fallback to local file on API error
        local_file = CONFIG_DIR / f"{page_type}_locators.json"
        if local_file.exists():
            with open(local_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        raise HTTPException(status_code=500, detail=f"Failed to fetch locators: {str(e)}")

@app.post("/tests/run/{page_type}")
async def run_tests(page_type: str, background_tasks: BackgroundTasks):
    """Run Playwright tests for specific page type"""
    page_type = page_type.lower()
    
    # Try to find the test file (it might have different casing)
    test_path = TESTS_DIR / page_type / f"test_{page_type}.py"
    if not test_path.exists():
        # Fallback to checking any case if needed, but generate_script now normalizes to lowercase
        raise HTTPException(status_code=404, detail=f"Test file not found for page: {page_type}")
    
    try:
        cmd = [sys.executable, "-m", "pytest", str(test_path), "-v", "--tb=short"]
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=300)
        
        return {
            "status": "completed",
            "page_type": page_type,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "artifacts_available": f"/artifacts/{page_type}"
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "message": "Test execution timed out after 5 minutes"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test execution failed: {str(e)}")

class HandoverRequest(BaseModel):
    run_id: str
    locators_path: Optional[str] = None
    target_url: Optional[str] = None

# Store simple job status for WebSocket
jobs: Dict[str, Dict] = {}

def run_generation_task(run_id: str):
    """Background task to run the generation script without blocking the server"""
    jobs[run_id] = {"status": "running"}
    try:
        logger.info(f"Starting background generation for job: {run_id}")
        cmd = [sys.executable, "generate_script.py"]
        
        # Use Popen to stream output to terminal in real-time
        process = subprocess.Popen(
            cmd, 
            cwd=PROJECT_ROOT, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, # Merge stderr into stdout
            text=True, 
            bufsize=1, 
            universal_newlines=True
        )
        
        stdout_buffer = []
        
        # Stream output
        if process.stdout:
            for line in process.stdout:
                print(line, end='') # Print to live terminal
                stdout_buffer.append(line)
        
        process.wait()
        full_output = "".join(stdout_buffer)
        
        if process.returncode == 0:
            # Calculate metrics
            test_files_count = len(list(TESTS_DIR.rglob("test_*.py")))
            
            jobs[run_id] = {
                "status": "completed",
                "result": {
                    "stdout": full_output,
                    "stderr": "",
                    "metrics": {
                        "scripts_generated": test_files_count,
                        "pages_covered": test_files_count
                    }
                }
            }
            logger.info(f"Background generation for {run_id} completed successfully.")
            
            # --- BRIDGE TO CI/CD (Executor) ---
            try:
                # Robustly find project root
                current_file_path = Path(__file__).resolve()
                root_dir = None
                
                # Search upwards for a clear marker
                search_ptr = current_file_path
                for _ in range(10):
                    if (search_ptr / "package.json").exists() or \
                       (search_ptr.name.lower() in ["qa_garden-main", "qa-garden-dashboard"]):
                        root_dir = search_ptr
                        break
                    if search_ptr.parent == search_ptr:
                        break
                    search_ptr = search_ptr.parent
                
                # Fallback
                if not root_dir:
                    root_dir = PROJECT_ROOT.parent
                
                logger.info(f"Using project root for bridging to CI/CD: {root_dir}")
                
                if (root_dir / "agents" / "cicd").exists():
                    cicd_base = root_dir / "agents" / "cicd"
                else:
                    cicd_base = root_dir / "cicd"

                if cicd_base.exists():
                    import shutil
                    import time
                    
                    # Helper for robust deletion (handle read-only/locked files)
                    def robust_cleanup(path: Path):
                        if not path.exists():
                            return
                        try:
                            import stat
                            # On Windows, we try to clear files first, then delete if possible
                            # but it's safer to just empty the folder to avoid 'Access Denied' on the folder itself
                            for item in path.iterdir():
                                try:
                                    if item.is_file():
                                        item.chmod(stat.S_IWRITE)
                                        item.unlink()
                                    elif item.is_dir():
                                        shutil.rmtree(item, ignore_errors=True)
                                except Exception as e:
                                    logger.warning(f"Could not delete {item}: {e}")
                        except Exception as e:
                            logger.warning(f"Error during robust cleanup of {path}: {e}")

                    # Log source status
                    source_tests = list((PROJECT_ROOT / "tests").glob("**/*.py"))
                    logger.info(f"Bridge Source: Found {len(source_tests)} test files in {PROJECT_ROOT / 'tests'}")

                    # Copy to CI/CD agent
                    for folder in ["tests", "config", "testcases"]:
                        src_path = PROJECT_ROOT / folder
                        dest_path = cicd_base / folder
                        
                        # 1. Ensure destination exists
                        dest_path.mkdir(parents=True, exist_ok=True)

                        # 2. CLEAR destination to prevent stale test inflation
                        logger.info(f"Cleaning destination: {dest_path}")
                        robust_cleanup(dest_path)

                        # 3. Copy (Merge/Overwrite content)
                        try:
                            shutil.copytree(
                                src_path, 
                                dest_path, 
                                dirs_exist_ok=True, 
                                ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.git')
                            )
                        except Exception as copy_err:
                            logger.error(f"Failed to bridge {folder}: {copy_err}")

                    logger.info(f"Bridged files to CI/CD agent at: {cicd_base}")
            except Exception as bridge_err:
                logger.error(f"Failed to bridge to CI/CD: {bridge_err}")

            # --- TRIGGER CI/CD AGENT ---
            try:
                # Use environment variable for CI/CD URL or fallback to localhost:8003 (direct port)
                cicd_endpoint = os.getenv("CICD_AGENT_URL", "http://localhost:8003")
                cicd_url = f"{cicd_endpoint}/generate/tests"
                logger.info(f"Triggering CI/CD Agent at {cicd_url}...")
                
                response = requests.post(cicd_url, json={"run_id": run_id}, timeout=5)
                if response.status_code in [200, 202]:
                    logger.info(f"Successfully triggered CI/CD for {run_id}")
                else:
                    logger.error(f"CI/CD Trigger failed with status {response.status_code}: {response.text}")
                    
            except Exception as trigger_err:
                logger.error(f"Failed to trigger CI/CD Agent: {trigger_err}")
            # ---------------------------
        else:
            jobs[run_id] = {"status": "failed", "error": full_output}
            logger.error(f"Background generation for {run_id} failed: {full_output}")
    except Exception as e:
        jobs[run_id] = {"status": "failed", "error": str(e)}
        logger.error(f"Exception in background generation {run_id}: {str(e)}")

@app.websocket("/ws/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    await websocket.accept()
    logger.info(f"WebSocket connected for job: {run_id}")
    
    try:
        while True:
            # Check current job status
            job_data = jobs.get(run_id, {"status": "waiting"})
            status = job_data["status"]
            
            # Map internal status to frontend expectations
            event = "progress"
            if status == "completed":
                event = "completed"
            elif status == "failed":
                event = "error"
                
            # Extract metrics if available
            result_data = job_data.get("result", {})
            metrics = result_data.get("metrics", None)

            await websocket.send_json({
                "event": event,
                "agent": "script_generator",
                "status": status,
                "percent": 100 if status == "completed" else 50 if status == "running" else 10,
                "metrics": metrics,
                "data": result_data
            })
            
            if status in ["completed", "failed"]:
                # Keep alive so frontend hook is happy during handover
                logger.info(f"WebSocket: Job {run_id} transitioned to {status}. Keeping alive.")
                try:
                    while True:
                        await websocket.receive_text()
                except WebSocketDisconnect:
                    break
                
            await asyncio.sleep(2)
    except Exception as e:
        logger.error(f"WebSocket error for {run_id}: {e}")
    finally:
        if websocket.client_state != WebSocketState.DISCONNECTED:
            try:
                await websocket.close()
            except:
                pass

@app.post("/generate/tests")
async def generate_tests(request: HandoverRequest, background_tasks: BackgroundTasks):
    """Trigger test generation in the background"""
    run_id = request.run_id
    
    # Optional Security: If a path is provided, validate it's within project root
    if request.locators_path:
        loc_path = Path(request.locators_path).resolve()
        # Basic check to ensure path is within current working directory or subfolders
        if str(PROJECT_ROOT.parent) not in str(loc_path):
             logger.warning(f"External path provided for generation: {loc_path}. Proceeding with caution.")

    # If already running, don't start again
    if jobs.get(run_id, {}).get("status") == "running":
        return {"status": "running", "message": "Generation already in progress"}
        
    background_tasks.add_task(run_generation_task, run_id)
    
    return {
        "status": "started",
        "run_id": run_id,
        "message": "Test generation triggered in background"
    }

@app.post("/automation/full/{page_type}")
async def full_automation(page_type: str, background_tasks: BackgroundTasks):
    """Complete automation: fetch → generate → test → store results"""
    page_type = page_type.lower()
    
    try:
        # Step 1: Fetch testcases and locators from friend's API
        testcases_result = await get_testcases(page_type)
        locators_result = await get_locators(page_type)
        
        # Step 2: Generate tests using LLM
        generation_result = await generate_tests()
        
        # Step 3: Run tests with pytest
        test_result = await run_tests(page_type, background_tasks)
        
        # Step 4: Results are automatically stored by existing endpoints
        return {
            "status": "automation_completed",
            "page_type": page_type,
            "steps_completed": {
                "testcases_fetched": bool(testcases_result),
                "locators_fetched": bool(locators_result),
                "tests_generated": generation_result["status"] == "completed",
                "tests_executed": test_result["status"] == "completed"
            },
            "test_result": test_result,
            "artifacts_available": f"/artifacts/{page_type}",
            "results_available": f"/results/{page_type}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Full automation failed: {str(e)}")

@app.get("/results/{page_type}")
async def get_results(page_type: str):
    """Get test execution results and summary"""
    page_type = page_type.lower()
    
    # Get artifacts for summary
    artifacts = await get_artifacts(page_type)
    
    # Parse log files for pass/fail counts
    logs_path = TEST_LOGS_DIR / page_type
    test_summary = {
        "total_tests": 0,
        "passed_tests": 0,
        "failed_tests": 0
    }
    
    if logs_path.exists():
        for log_file in logs_path.glob("*.log"):
            test_summary["total_tests"] += 1
            try:
                content = log_file.read_text(encoding='utf-8')
                # Look for different pass/fail patterns
                if any(pattern in content for pattern in ["✅ PASSED", "PASSED", "passed"]):
                    test_summary["passed_tests"] += 1
                elif any(pattern in content for pattern in ["❌ FAILED", "FAILED", "failed", "ERROR", "error"]):
                    test_summary["failed_tests"] += 1
            except Exception:
                pass
    
    # If no pass/fail found in logs, try to get from pytest HTML report
    report_file = ARTIFACTS_DIR / "reports" / "report.html"
    if report_file.exists() and test_summary["passed_tests"] == 0 and test_summary["failed_tests"] == 0:
        try:
            report_content = report_file.read_text(encoding='utf-8')
            # Parse HTML report for results
            import re
            passed_match = re.search(r'(\d+)\s+passed', report_content)
            failed_match = re.search(r'(\d+)\s+failed', report_content)
            if passed_match:
                test_summary["passed_tests"] = int(passed_match.group(1))
            if failed_match:
                test_summary["failed_tests"] = int(failed_match.group(1))
        except Exception:
            pass
    
    return {
        "page_type": page_type,
        "test_summary": test_summary,
        "artifacts_count": {
            "screenshots": len(artifacts["screenshots"]),
            "videos": len(artifacts["videos"]),
            "logs": len(artifacts["logs"])
        },
        "artifacts": artifacts,
        "report_available": "/artifacts/reports/report.html" if report_file.exists() else None,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/artifacts/{page_type}")
async def get_artifacts(page_type: str):
    """Get available artifacts for a page type"""
    page_type = page_type.lower()
    
    artifacts = {
        "page_type": page_type,
        "screenshots": [],
        "videos": [],
        "logs": []
    }
    
    # Get screenshots
    screenshots_path = SCREENSHOTS_DIR / page_type
    if screenshots_path.exists():
        artifacts["screenshots"] = [f.name for f in screenshots_path.glob("*.png")]
    
    # Get videos
    videos_path = VIDEOS_DIR / page_type
    if videos_path.exists():
        artifacts["videos"] = [f.name for f in videos_path.glob("*.webm")]
    
    # Get logs
    logs_path = TEST_LOGS_DIR / page_type
    if logs_path.exists():
        artifacts["logs"] = [f.name for f in logs_path.glob("*.log")]
    
    return artifacts

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8002)