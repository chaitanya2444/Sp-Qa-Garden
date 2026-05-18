from pydantic import BaseModel
from typing import List, Optional


class FailureInput(BaseModel):
    test_name: str
    file_path: str
    error_message: str
    stack_trace: str
    logs: Optional[str] = None
    source_code: Optional[str] = None
    screenshot: Optional[str] = None  # Base64 encoded screenshot
    page_source: Optional[str] = None # HTML source of the page

    # dynamic settings from frontend/client
    run_id: Optional[str] = None         # dashboard run ID for websocket broadcast
    llm_model: str                       # e.g. "gemma:2b"
    bert_url: str                        # e.g. "http://localhost:8001/triage"
    labels: Optional[List[str]] = None   # optional list of labels
    test_url: Optional[str] = None       # optional URL of the page being tested (e.g., "https://example.com/login")
    playwright_script_url: Optional[str] = None  # optional playwright script URL (e.g., "file:///C:/tests/login.spec.js#L25")
    playwright_script_endpoint: Optional[str] = None  # optional endpoint URL to retrieve/execute Playwright scripts (e.g., "http://playwright-service.com/api/scripts/login-test")


class TriageOutput(BaseModel):
    title: str
    description: str
    raw_failure_text: str
    stack_trace: Optional[str] = None
    status: str
    error_line: Optional[int] = None
    playwright_script: Optional[str] = None  # Clickable file:// URL with line number anchor (e.g., file:///path/to/file.js#L42)
    test_url: Optional[str] = None  # Clickable URL of the page being tested (e.g., https://example.com/login)
    playwright_script_endpoint: Optional[str] = None  # Endpoint URL for external Playwright script service
    triage_label: Optional[str] = None  # Intelligent label for error categorization (e.g., "Assertion: Title Mismatch", "Timeout Error")
    # Metadata fields (added when stored)
    id: Optional[str] = None
    created_at: Optional[str] = None
    run_id: Optional[str] = None


class TriageResultList(BaseModel):
    """Response model for listing multiple triage results"""
    total: int
    results: List[TriageOutput]
