from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import subprocess
import json
import sys
import os
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel
import logging
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from starlette.websockets import WebSocketState
import xml.etree.ElementTree as ET

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="QA Garden UI/UX Test Automation API",
    description="API for managing Playwright test automation, test generation, and artifact management",
    version="1.0.0"
)

# Enable CORS
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

# Store job status for WebSocket
jobs: Dict[str, Dict] = {}

def get_available_pages() -> List[str]:
    """Dynamically discover available page types from local files"""
    pages = set()
    # Check testcases
    for f in TESTCASES_DIR.glob("*_testcases.json"):
        pages.add(f.stem.replace("_testcases", "").lower())
    # Check tests
    if (PROJECT_ROOT / "tests").exists():
        for d in (PROJECT_ROOT / "tests").iterdir():
            if d.is_dir():
                pages.add(d.name.lower())
    return sorted(list(pages))

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
            "test_execution": "/tests/run/{page_type}",
            "test_generation": "/generate/tests",
            "artifacts": "/artifacts/{page_type}",
            "test_cases": "/testcases/{page_type}",
            "test_results": "/results/{page_type}",
            "locators": "/config/locators/{page_type}"
        }
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "project_root": str(PROJECT_ROOT)
    }

@app.websocket("/ws/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    await websocket.accept()
    logger.info(f"WebSocket connected for job: {run_id}")
    
    try:
        while True:
            # Check current job status
            job_data = jobs.get(run_id, {"status": "waiting"})
            status = job_data["status"]
            
            # Determine event type based on status
            event_type = "progress"
            if status == "completed":
                event_type = "completed"
            elif status == "failed":
                event_type = "error"

            # Construct payload
            payload = {
                "event": event_type,
                "agent": "executor",
                "status": status,
                "percent": job_data.get("percent", 100 if status == "completed" else 50 if status == "running" else 10),
                "data": job_data
            }
            
            # Lift metrics to top level for frontend convenience
            if "result" in job_data and "metrics" in job_data["result"]:
                payload["metrics"] = job_data["result"]["metrics"]
            
            # Map error field for frontend if failed
            if status == "failed":
                payload["error"] = job_data.get("error", "Unknown error")
                payload["message"] = job_data.get("error", "Unknown error")

            await websocket.send_json(payload)
            
            if status == "completed":
                # ALSO send pipeline_finished since this is the last agent
                await websocket.send_json({
                    "event": "pipeline_finished",
                    "run_id": run_id
                })
            
            if status in ["completed", "failed"]:
                # Keep alive until client disconnects
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

@app.get("/testcases/{page_type}")
async def get_testcases(page_type: str):
    """Get test cases from external API and save locally"""
    # Security: Sanitize page_type to prevent path traversal
    if not page_type.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid page_type format")
    
    page_type = page_type.lower()
    available_pages = get_available_pages()
    
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
    """Get locators from external API and save as Python file"""
    # Security: Sanitize page_type
    if not page_type.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid page_type format")
        
    page_type = page_type.lower()
    
    try:
        # Try to fetch from external API first
        if EXTERNAL_API_BASE_URL:
            external_url = f"{EXTERNAL_API_BASE_URL}/config/locators/{page_type}"
            
            response = requests.get(external_url, timeout=10)
            if response.status_code == 200:
                locators_data = response.json()
                
                # Save to local Python file as a class (better for LLM)
                class_name = "".join([word.capitalize() for word in page_type.split("_")]) + "Locators"
                local_file = CONFIG_DIR / f"{page_type}_locators.py"
                with open(local_file, 'w', encoding='utf-8') as f:
                    f.write(f"# {page_type.title()} Page Locators\n")
                    f.write(f"class {class_name}:\n")
                    if not locators_data:
                        f.write("    pass\n")
                    else:
                        for key, value in locators_data.items():
                            # Sanitize key for python variable name
                            safe_key = key.replace("-", "_").replace(" ", "_").upper()
                            
                            # Extract clean selector from Playwright commands
                            import re
                            def cleanup_locator(val):
                                if not isinstance(val, str): return val
                                # page.locator('#id') -> #id
                                m = re.search(r"page\.locator\(['\"](.+?)['\"]\)", val)
                                if m: return m.group(1)
                                
                                # page.getByRole('link', { name: 'Foo' }) -> a:has-text("Foo")
                                m = re.search(r"page\.getByRole\(['\"](.+?)['\"],\s*\{\s*name:\s*['\"](.+?)['\"]\s*\}", val)
                                if m:
                                    role, name = m.groups()
                                    if role == 'link': return f"a:has-text(\"{name}\")"
                                    if role == 'button': return f"button:has-text(\"{name}\")"
                                    return f"role={role}[name=\"{name}\"]"

                                # page.getByText('Foo', ...) -> text=Foo
                                m = re.search(r"page\.getByText\(['\"](.+?)['\"]", val)
                                if m: return f"text=\"{m.group(1)}\""
                                
                                # page.getByLabel('Foo') -> label:has-text("Foo")
                                m = re.search(r"page\.getByLabel\(['\"](.+?)['\"]", val)
                                if m: return f"label:has-text(\"{m.group(1)}\")"

                                return val

                            clean_value = cleanup_locator(value)
                            f.write(f"    {safe_key} = {json.dumps(clean_value)}\n")
                
                return locators_data
        
        # Fallback to local file
        local_file = CONFIG_DIR / f"{page_type}_locators.py"
        if local_file.exists():
            with open(local_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Extract locators from Python file
                import ast
                tree = ast.parse(content)
                for node in tree.body:
                    if isinstance(node, ast.Assign):
                        return ast.literal_eval(node.value)
        
        raise HTTPException(status_code=404, detail=f"Locators not found for {page_type}")
        
    except requests.exceptions.RequestException as e:
        # Fallback to local file on API error
        local_file = CONFIG_DIR / f"{page_type}_locators.py"
        if local_file.exists():
            with open(local_file, 'r', encoding='utf-8') as f:
                content = f.read()
                import ast
                tree = ast.parse(content)
                for node in tree.body:
                    if isinstance(node, ast.Assign):
                        return ast.literal_eval(node.value)
        raise HTTPException(status_code=500, detail=f"Failed to fetch locators: {str(e)}")

@app.post("/tests/run/{page_type}")
async def run_tests(page_type: str, background_tasks: BackgroundTasks):
    """Run Playwright tests for specific page type"""
    page_type = page_type.lower()
    
    test_path = TESTS_DIR / page_type / f"test_{page_type}.py"
    if not test_path.exists():
        raise HTTPException(status_code=404, detail=f"Test file not found: {test_path}")
    
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

def sync_failures_to_triage(xml_path: Path, run_id: str):
    """
    Parse JUnit XML and send failures to Triage Engine.
    This acts as a safety net if the real-time hook fails or crashes.
    """
    if not xml_path.exists():
        logger.warning(f"No XML report found at {xml_path}, skipping Triage sync.")
        return

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        failure_count = 0
        for testcase in root.iter("testcase"):
            # Check for failure or error
            failure = testcase.find("failure")
            error = testcase.find("error")
            
            if failure is not None or error is not None:
                # Construct payload
                error_node = failure if failure is not None else error
                error_message = error_node.get("message", "Unknown Error")
                stack_trace = error_node.text or ""
                
                payload = {
                    "run_id": run_id,
                    "test_name": f"{testcase.get('classname')}::{testcase.get('name')}",
                    "file_path": testcase.get("file", "unknown"),
                    "error_message": error_message,
                    "stack_trace": stack_trace,
                    "source_code": "Source unavailable in XML fallback",
                    "screenshot": None, # XML doesn't have screenshots
                    "llm_model": os.getenv("OLLAMA_MODEL", "llama3.2:3b"),  # Use Ollama model from env
                    "bert_url": "", # Disabled to prevent 404s
                    "timestamp": datetime.now().isoformat()
                }
                
                try:
                    # Use environment variable for Triage Engine URL or fallback to localhost:8004 (direct port)
                    triage_endpoint = os.getenv("TRIAGE_ENGINE_URL", "http://localhost:8004")
                    triage_url = f"{triage_endpoint}/api/triage"
                    
                    requests.post(triage_url, json=payload, timeout=15)
                    failure_count += 1
                except Exception as req_err:
                    logger.error(f"Failed to sync failure to Triage: {req_err}")
                    
        logger.info(f"Synced {failure_count} failures to Triage Engine from XML report.")
        
        # FINAL SIGNAL: Mark run as completed in Triage Engine
        try:
            triage_endpoint = os.getenv("TRIAGE_ENGINE_URL", "http://localhost:8004")
            requests.post(f"{triage_endpoint}/api/complete/{run_id}", timeout=10)
            logger.info(f"Sent completion signal to Triage Engine for run: {run_id}")
        except Exception as e:
            logger.error(f"Failed to send completion signal to Triage: {e}")
        
    except Exception as e:
        logger.error(f"Error parsing XML report for Triage sync: {e}")

class HandoverRequest(BaseModel):
    run_id: str
    target_path: Optional[str] = None # Optional for future-proofing path-based handovers

@app.post("/handover")
async def trigger_handover(request: HandoverRequest, background_tasks: BackgroundTasks):
    """
    Trigger triage process for a completed run.
    Moves triage sync to background to prevent blocking.
    """
    run_id = request.run_id
    logger.info(f"Triggering Triage handover for run: {run_id}")
    
    xml_path = ARTIFACTS_DIR / f"results_{run_id}.xml"
    if xml_path.exists():
        # RUN IN BACKGROUND
        background_tasks.add_task(sync_failures_to_triage, xml_path, run_id)
    else:
        logger.warning(f"No XML report found for run {run_id}, handover skipped.")
        
    return {"status": "accepted", "message": "Triage sync initiated in background"}

def run_simulation_task(run_id: str, background_tasks: BackgroundTasks):
    """Execute CI/CD pipeline: Verify files -> Run Tests -> Report Results"""
    jobs[run_id] = {"status": "running"}
    logger.info(f"Starting CI/CD execution for job: {run_id}")
    
    # 1. Verify files exist
    test_files = list(TESTS_DIR.rglob("test_*.py"))
    if not test_files:
        jobs[run_id] = {"status": "failed", "error": "No test files found to execute."}
        return

    logger.info(f"Found {len(test_files)} test files. Starting execution...")
    
    # 2. Run Pytest recursively on tests folder
    try:
        # Pass TRIAGE_RUN_ID to pytest via environment variables
        env = os.environ.copy()
        env["TRIAGE_RUN_ID"] = run_id
        
        # Use sys.executable to ensure we use the correct python env
        # removed -n auto to improve stability (prevent crashes/race conditions)
        # added --junitxml to capture results reliably for post-processing
        cmd = [sys.executable, "-m", "pytest", str(TESTS_DIR), "-v", "--tb=short", f"--html={ARTIFACTS_DIR}/report_{run_id}.html", f"--junitxml={ARTIFACTS_DIR}/results_{run_id}.xml"]
        
        # Increased timeout to 3600s (1 hour) to handle large test suites
        process = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=3600, env=env)
        
        stdout = process.stdout
        stderr = process.stderr
        exit_code = process.returncode
        
        status = "completed"
        # Pytest exit codes: 0=All passed, 1=Tests failed, 2=Interrupted, 3=Internal error, 4=Usage error, 5=No tests collected
        if exit_code != 0: 
             logger.warning(f"Pytest finished with exit code {exit_code} (Tests Failed or Error). Marking as completed for Triage.")
             logger.error(f"Stderr: {stderr}")
             # We rely on metrics to indicate failure to the frontend
        
        # Parse summary from stdout
        # Example: "=== 1 failed, 4 passed in 2.5s ==="
        summary_line = "Execution completed."
        passed_count = 0
        failed_count = 0
        total_count = 0
        
        import re
        def strip_ansi(text):
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            return ansi_escape.sub('', text)
        
        # Parse stdout for summary and specific counts
        # improved logic to handle potential multiline or partial output
        for line in stdout.splitlines():
            clean_line = strip_ansi(line)
            
            # 1. Capture "collected X items" as a fallback total
            if "collected" in clean_line and "items" in clean_line:
                 c_match = re.search(r'collected\s+(\d+)\s+items', clean_line)
                 if c_match: total_count = int(c_match.group(1))

            # 2. Capture passed/failed/error counts
            if "passed" in clean_line or "failed" in clean_line or "error" in clean_line:
                 p_match = re.search(r'(\d+)\s+passed', clean_line)
                 f_match = re.search(r'(\d+)\s+failed', clean_line)
                 e_match = re.search(r'(\d+)\s+error', clean_line)
                 if p_match: passed_count = max(passed_count, int(p_match.group(1)))
                 if f_match: failed_count = max(failed_count, int(f_match.group(1)))
                 if e_match: failed_count += int(e_match.group(1)) # Treat errors as failures
                 
            # 3. Capture "summary" line for message
            if clean_line.startswith("===") and ("passed" in clean_line or "failed" in clean_line):
                summary_line = clean_line.strip("= ")

        # Special handling for Collection Errors (Exit Code != 0 and No Failure Count)
        if exit_code != 0 and failed_count == 0 and passed_count == 0:
            logger.error("Pytest failed without reporting failed tests (likely Collection Error). Forcing failure count.")
            failed_count = 1
            total_count = 1
            summary_line = "Collection/System Error"

        # Recalculate total if passed+failed > collected (or if collected was missed)
        if (passed_count + failed_count) > total_count:
            total_count = passed_count + failed_count
        elif total_count == 0 and (passed_count + failed_count) > 0:
            total_count = passed_count + failed_count

        # --- XML Fallback Sync ---
        # Ensure Triage gets failures even if real-time hook missed them (Backgrounded)
        try:
             xml_path = ARTIFACTS_DIR / f"results_{run_id}.xml"
             if xml_path.exists():
                 # background_tasks is available here because we passed it from the route
                 background_tasks.add_task(sync_failures_to_triage, xml_path, run_id)
             else:
                 logger.warning(f"XML report not found at {xml_path}")
        except Exception as sync_err:
             logger.error(f"XML Sync backgrounding failed: {sync_err}")
        # -------------------------
        
        metrics = {
            "total_tests": total_count,
            "passed": passed_count,
            "failed": failed_count,
            "success_rate": round((passed_count / total_count * 100) if total_count > 0 else 0, 1)
        }
        
        jobs[run_id] = {
            "status": status,
            "percent": 100,
            "result": {
                "message": f"Test Execution Finished: {summary_line}",
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "metrics": metrics,
                "report_available": "/artifacts/report.html"
            }
        }
        logger.info(f"CI/CD execution for {run_id} finished with code {exit_code}")
        
    except Exception as e:
        jobs[run_id] = {"status": "failed", "error": str(e)}
        logger.error(f"CI/CD execution failed: {e}")

@app.post("/tests/run/all/{run_id}")
async def run_all_simulation(run_id: str, background_tasks: BackgroundTasks):
    """Trigger the full CI/CD simulation in a background task"""
    if run_id in jobs and jobs[run_id]["status"] == "running":
        raise HTTPException(status_code=400, detail="Job already running")
    
    background_tasks.add_task(run_simulation_task, run_id, background_tasks)
    return {"status": "started", "run_id": run_id, "message": "CI/CD preparation started"}

@app.post("/generate/tests")
async def generate_tests(request: HandoverRequest, background_tasks: BackgroundTasks):
    """Handle handover from Playwright Gen"""
    run_id = request.run_id
    
    if jobs.get(run_id, {}).get("status") == "running":
        return {"status": "running", "message": "Already in progress"}
        
    background_tasks.add_task(run_simulation_task, run_id, background_tasks)
    
    return {
        "status": "started",
        "run_id": run_id,
        "message": "CI/CD preparation started"
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
    uvicorn.run(app, host="127.0.0.1", port=8003)