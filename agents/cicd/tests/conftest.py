import sys
from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright, expect
import logging
import datetime
import time
import threading

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()

@pytest.fixture
def context(browser):
    context = browser.new_context()
    yield context
    context.close()

@pytest.fixture
def page(context):
    page = context.new_page()
    yield page
    page.close()

@pytest.fixture
def authenticated_page(context):
    """Generic authenticated page fixture. Fallback to simple page if no LOGIN_URL."""
    page = context.new_page()
    try:
        from config.urls import LOGIN_URL
        page.goto(LOGIN_URL, timeout=60000)
    except (ImportError, AttributeError):
        # Fallback for sites without explicit login
        pass
    
    page.wait_for_load_state("networkidle")
    yield page
    page.close()

# --- TRIAGE REPORTING HOOK ---
import os
import requests
import base64

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    '''
    Hook to capture test failures and send them to the Triage Engine.
    Includes screenshot and source code context.
    '''
    # Execute all other hooks to obtain the report object
    outcome = yield
    report = outcome.get_result()
    
    # We only care about failures during call (execution) or setup
    if report.when == "call" and report.failed:
        try:
            # 1. Capture Screenshot
            screenshot_b64 = None
            if "page" in item.funcargs:
                page = item.funcargs["page"]
                screenshot_bytes = page.screenshot(type="jpeg", quality=50)
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
            elif "authenticated_page" in item.funcargs:
                page = item.funcargs["authenticated_page"]
                screenshot_bytes = page.screenshot(type="jpeg", quality=50)
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

            # 2. Get Source Code
            source_code = ""
            try:
                # Read the test file
                with open(item.fspath, "r", encoding="utf-8") as f:
                    source_code = f.read()
            except Exception as e:
                source_code = f"Could not read source: {e}"

            # 3. Check for Run ID
            run_id = os.environ.get("TRIAGE_RUN_ID", "default_manual_run")

            # 4. Payload for Triage Engine
            payload = {
                "run_id": run_id,
                "test_name": item.nodeid,
                "file_path": str(item.fspath),
                "error_message": str(report.longrepr),
                "stack_trace": str(report.longrepr),  # Pytest longrepr contains trace
                "source_code": source_code,
                "screenshot": screenshot_b64,
                "llm_model": "gemini-pro", # Default model for Triage analysis
                "bert_url": "", # BERT disabled (using pattern matching fallback) to avoid 404s
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            # 5. Send to Triage Engine (Fire and Forget to avoid blocking)
            def send_report():
                try:
                    requests.post("http://localhost:8004/api/triage", json=payload, timeout=2)
                except Exception as e:
                    print(f"Failed to report to Triage: {e}")

            threading.Thread(target=send_report).start()
            
        except Exception as e:
            print(f"Error in Triage Hook: {e}")