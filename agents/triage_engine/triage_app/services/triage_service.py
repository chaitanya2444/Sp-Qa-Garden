from typing import Any, Dict, Optional, List, Tuple
import os
import re




from app.services.playwright_label_detector import detect_playwright_label
from app.schemas import FailureInput
from app.utils.url_utils import format_file_url_with_line, extract_test_url_from_logs
from app.socket_manager import manager
import asyncio
from fastapi.concurrency import run_in_threadpool





def _extract_error_message(failure_text: str) -> str:
    for line in failure_text.splitlines():
        if line.startswith("Error Message:"):
            return line.split("Error Message:", 1)[1].strip()
    return ""


def _rule_based_category(failure_text: str) -> str:
    """
    Basic rule-based triage using keywords in the failure text.
    Returns one of: 'frontend_ui', 'backend_api', 'database',
    'performance', 'infrastructure', 'authentication', 'unknown'
    """
    em = _extract_error_message(failure_text).lower()
    full = failure_text.lower()

    # Frontend / UI (Selenium, Playwright, React UI)
    if (
        "noselementexception" in em
        or "unable to locate element" in em
        or "selenium" in full
        or "playwright" in full
        or ("button" in full and "click" in full)
        or "#edit-" in full
        or "component" in full and ("render" in full or "props" in full)
        or "cannot read properties of undefined" in em
        or "cannot read property" in em
    ):
        return "frontend_ui"

    # Database
    if (
        "psycopg2" in em
        or "sql" in em
        or "database" in em
        or "connection timed out" in em
        or ("timeout" in em and "query" in full)
        or "deadlock" in full
    ):
        return "database"

    # Authentication / auth
    if (
        "unauthorized" in em
        or "forbidden" in em
        or "authentication" in full
        or "jwt" in full
        or "token expired" in full
    ):
        return "authentication"

    # Performance / timeout
    if (
        "timeout" in em
        or "took too long" in full
        or "slow response" in full
        or "latency" in full
    ):
        return "performance"

    # Backend / API
    if (
        "internal server error" in em
        or "status code 500" in em
        or "status code 5" in em
        or "500" in em
        or "api" in full
        or "endpoint" in full
        or "response code" in full
    ):
        return "backend_api"

    # Infrastructure / network
    if (
        "connection refused" in em
        or "host unreachable" in em
        or "dns" in full
        or "gateway" in full
        or "service unavailable" in em
    ):
        return "infrastructure"

    return "unknown"


def _map_category_to_labels(category: str, labels: Optional[List[str]]) -> str:
    """
    Map the internal category to one of the user-provided labels (if any).
    If no labels match, fallback to the first label or the category itself.
    """
    if not labels or len(labels) == 0:
        return category

    cat = category.lower()

    # direct match
    for lab in labels:
        if lab.lower() == cat:
            return lab

    # fuzzy mapping
    for lab in labels:
        l = lab.lower()
        if cat == "frontend_ui" and ("ui" in l or "front" in l or "view" in l):
            return lab
        if cat == "backend_api" and ("api" in l or "back" in l or "service" in l):
            return lab
        if cat == "database" and ("db" in l or "data" in l or "sql" in l):
            return lab
        if cat == "performance" and ("perf" in l or "latency" in l or "timeout" in l):
            return lab
        if cat == "infrastructure" and ("infra" in l or "network" in l or "server" in l):
            return lab
        if cat == "authentication" and ("auth" in l or "login" in l or "token" in l):
            return lab

    # fallback: just return the first candidate
    return labels[0]



async def process_failure(payload: FailureInput) -> Dict[str, Any]:
    failure_text = f"""
Test Name: {payload.test_name}
File Path: {payload.file_path}
Error Message: {payload.error_message}
Stack Trace: {payload.stack_trace}
Logs: {payload.logs}
""".strip()

    # 1) Bug report via AI (Gemini or Ollama)
    try:
        bug = None
        errors = []

        # 1. Try Gemini (Primary per user request) - High Limits & Free
        if os.getenv("GEMINI_API_KEY"):
            try:
                if payload.run_id:
                    await manager.broadcast(payload.run_id, {
                        "event": "progress",
                        "agent": "triage",
                        "status": "running",
                        "message": f"Analyzing {payload.test_name} with Gemini AI..."
                    })
                from app.services.gemini_service import generate_bug_report_with_gemini
                print(f"Attempting Gemini AI for: {payload.test_name}")
                # Run sync LLM call in threadpool
                bug = await run_in_threadpool(generate_bug_report_with_gemini, failure_text)
            except Exception as e:
                msg = f"Gemini failed: {e}"
                print(msg)
                errors.append(msg)

        # 2. Try Groq (Secondary Fallback) - Fast & High Quality
        if not bug and os.getenv("GROQ_API_KEY"):
            try:
                if payload.run_id:
                    await manager.broadcast(payload.run_id, {
                        "event": "progress",
                        "agent": "triage",
                        "status": "running",
                        "message": f"Falling back to Groq AI for {payload.test_name}..."
                    })
                from app.services.groq_service import generate_bug_report_with_groq
                print(f"Attempting Groq AI for: {payload.test_name}")
                # Run sync LLM call in threadpool
                bug = await run_in_threadpool(generate_bug_report_with_groq, failure_text)
            except Exception as e:
                msg = f"Groq failed: {e}"
                print(msg)
                errors.append(msg)

        # 3. Try Ollama (Local) - ONLY if explicitly configured (skipped on cloud/HF Spaces)
        if not bug and os.getenv("OLLAMA_BASE_URL", ""):
            try:
                if payload.run_id:
                    await manager.broadcast(payload.run_id, {
                        "event": "progress",
                        "agent": "triage",
                        "status": "running",
                        "message": f"Falling back to local AI (Ollama)..."
                    })
                from app.services.ollama_service import generate_bug_report
                print(f"Attempting Ollama ({payload.llm_model}) for: {payload.test_name}")
                # Run sync LLM call in threadpool
                bug = await run_in_threadpool(generate_bug_report, payload.llm_model, failure_text)
            except Exception as e:
                msg = f"Ollama failed: {e}"
                print(msg)
                errors.append(msg)

        # If all AI providers failed, fall through to Rule-Based Fallback
        if not bug:
            print("All AI providers failed. Using Rule-Based Fallback.")
            # Proceed to exception handler block which contains the fallback logic
            raise Exception(f"All LLMs failed: {'; '.join(errors)}")
            
    except Exception as e:
        print(f"AI Generation failed ({type(e).__name__}): {e}")
        # Fallback to Rule-Based Generation (Regex/Parsing)
        # This ensures we ALWAYS return a clean triage result even if the LLM is down/rate-limited.
        
        # Extract basic info for fallback
        err_msg = _extract_error_message(failure_text) or "Unknown Error"
        category = _rule_based_category(failure_text)
        
        # Clean up error message for title (take first 60 chars)
        clean_err = err_msg.split('\n')[0][:80]
        if len(clean_err) > 75: clean_err += "..."
        
        fallback_title = f"{category.replace('_', ' ').title()}: {clean_err}"
        
        fallback_desc = (
            f"The test failed with a **{category}** error.\n\n"
            f"**Error Message:** `{err_msg}`\n\n"
            f"**Analysis:** automated fallback analysis suggests this is related to {category.replace('_', ' ')}. "
            f"Please check the stack trace for the exact line number. (AI generation skipped due to rate limit/error)"
        )
        
        bug = {
            "title": fallback_title,
            "description": fallback_desc,
        }


    # 2) Extract extra structured fields INLINE
    
    # Extract error_line_number from stack trace using regex with FALLBACK logic
    error_line_number = None
    
    # Try extracting from stack trace first

    if payload.stack_trace:
        # Try patterns: "line XXX", ":XXX:", ":XXX)", "at file.py:XXX"
        line_match = re.search(r'line\s+(\d+)', payload.stack_trace, re.IGNORECASE)
        if not line_match:
            # Look for file.py:123 pattern (more specific)
            line_match = re.search(r'\.(py|js|ts|jsx|tsx):(\d+)', payload.stack_trace)
            if line_match:
                error_line_number = int(line_match.group(2))
        if not line_match:
            line_match = re.search(r':(\d+)\)', payload.stack_trace)
        if not line_match:
            line_match = re.search(r'at\s+[^\s]+:(\d+)', payload.stack_trace)
        if line_match and error_line_number is None:
            error_line_number = int(line_match.group(1))
    
    # FALLBACK 1: Try extracting from error_message if stack trace didn't work
    if error_line_number is None and payload.error_message:
        line_match = re.search(r'line\s+(\d+)', payload.error_message, re.IGNORECASE)
        if not line_match:
            # Look for file.py:123 pattern
            line_match = re.search(r'\.(py|js|ts|jsx|tsx):(\d+)', payload.error_message)
            if line_match:
                error_line_number = int(line_match.group(2))
        if not line_match:
            line_match = re.search(r':(\d+)\)', payload.error_message)
        if line_match and error_line_number is None:
            error_line_number = int(line_match.group(1))
    
    # FALLBACK 2: Try extracting from logs if still not found (but avoid timestamps)
    if error_line_number is None and payload.logs:
        # Only look for "line XXX" pattern in logs to avoid timestamp confusion
        line_match = re.search(r'line\s+(\d+)', payload.logs, re.IGNORECASE)
        if line_match:
            error_line_number = int(line_match.group(1))
    
    # Validate extracted line number (should be reasonable, not from timestamp)
    if error_line_number is not None and error_line_number > 10000:
        error_line_number = None  # Likely a false positive
    
    # FALLBACK 3: Default to line 1 if still not found (ALWAYS populate)
    if error_line_number is None:
        error_line_number = 1
    
    # Extract error_file_path from stack trace with FALLBACK logic
    error_file_path = None
    
    # Try extracting from stack trace first
    if payload.stack_trace:
        # PRIORITY 1: Look for test files specifically (test_*.py, *_test.py, *.spec.js, *.test.js)
        test_file_match = re.search(r'(test_[^\s]+\.(?:py|js|ts)|[^\s]+_test\.(?:py|js|ts)|[^\s]+\.spec\.(?:js|ts)|[^\s]+\.test\.(?:js|ts))', payload.stack_trace, re.IGNORECASE)
        if test_file_match:
            error_file_path = test_file_match.group(1)
        
        # PRIORITY 2: Look for File "path" pattern
        if not error_file_path:
            file_match = re.search(r'File\s+"([^"]+)"', payload.stack_trace)
            if file_match:
                error_file_path = file_match.group(1)
        
        # PRIORITY 3: Look for "at file.py:line" pattern
        if not error_file_path:
            file_match = re.search(r'at\s+([^\s:]+\.(?:py|js|ts|spec\.js|spec\.ts))', payload.stack_trace)
            if file_match:
                error_file_path = file_match.group(1)
        
        # PRIORITY 4: Generic file pattern (but avoid __init__.py)
        if not error_file_path:
            # Find all matching files
            all_files = re.findall(r'([^\s]+\.(?:py|js|ts|jsx|tsx|spec\.js|spec\.ts))', payload.stack_trace)
            # Filter out __init__.py and prioritize test files
            for file in all_files:
                if '__init__.py' not in file:
                    error_file_path = file
                    break
    
    # FALLBACK 1: Try extracting from error_message if stack trace didn't work
    if not error_file_path and payload.error_message:
        # Look for test files first
        test_file_match = re.search(r'(test_[^\s]+\.(?:py|js|ts)|[^\s]+_test\.(?:py|js|ts)|[^\s]+\.spec\.(?:js|ts))', payload.error_message, re.IGNORECASE)
        if test_file_match:
            error_file_path = test_file_match.group(1)
        
        if not error_file_path:
            file_match = re.search(r'File\s+"([^"]+)"', payload.error_message)
            if not file_match:
                file_match = re.search(r'([^\s]+\.(?:py|js|ts|jsx|tsx|spec\.js|spec\.ts))', payload.error_message)
            if file_match:
                error_file_path = file_match.group(1)
    
    # FALLBACK 2: Try extracting from logs if still not found
    if not error_file_path and payload.logs:
        # Look for test files first
        test_file_match = re.search(r'(test_[^\s]+\.(?:py|js|ts)|[^\s]+_test\.(?:py|js|ts)|[^\s]+\.spec\.(?:js|ts))', payload.logs, re.IGNORECASE)
        if test_file_match:
            error_file_path = test_file_match.group(1)
        
        if not error_file_path:
            file_match = re.search(r'File\s+"([^"]+)"', payload.logs)
            if not file_match:
                file_match = re.search(r'([^\s]+\.(?:py|js|ts|jsx|tsx|spec\.js|spec\.ts))', payload.logs)
            if file_match:
                error_file_path = file_match.group(1)
    
    # FALLBACK 3: Use file_path from payload if still not found
    if not error_file_path and payload.file_path:
        error_file_path = payload.file_path
    
    # FALLBACK 4: Use test_name as file path if everything else failed (ALWAYS populate)
    if not error_file_path:
        if payload.test_name:
            error_file_path = f"{payload.test_name}.unknown"
        else:
            error_file_path = "unknown_test_file"
    
    # Truncate stack_trace to max 3000 characters
    stack_trace_truncated = payload.stack_trace[:3000] if payload.stack_trace else None
    
    # Extract bug title and description for return
    bug_title = bug.get("title", "No title")
    bug_description = bug.get("description", "No description")
    
    # Convert file path to clickable URL with line number anchor
    # Use playwright_script_url from payload if provided, otherwise auto-generate
    if payload.playwright_script_url:
        playwright_script_url = payload.playwright_script_url
    else:
        playwright_script_url = format_file_url_with_line(error_file_path, error_line_number) if error_file_path else None

    # Extract test URL (the URL of the page being tested)
    test_url = None
    # Priority 1: Use test_url from payload if provided
    if payload.test_url:
        test_url = payload.test_url
    # Priority 2: Extract from logs
    elif payload.logs:
        test_url = extract_test_url_from_logs(payload.logs)
    # Priority 3: Extract from error message as fallback
    elif payload.error_message:
        test_url = extract_test_url_from_logs(payload.error_message)
    
    # Generate intelligent triage label using BERT classification
    triage_label = detect_playwright_label(
        error_message=payload.error_message,
        stack_trace=payload.stack_trace,
        failure_text=failure_text,
        bert_url=payload.bert_url
    )

    return {
        "title": bug_title,
        "description": bug_description,
        "raw_failure_text": failure_text,
        "stack_trace": stack_trace_truncated,
        "status": "failed",
        "error_line": error_line_number,
        "playwright_script": playwright_script_url,
        "test_url": test_url,
        "playwright_script_endpoint": payload.playwright_script_endpoint,
        "triage_label": triage_label,
        "run_id": payload.run_id,
        "test_name": payload.test_name,
    }

