import requests
import re

OLLAMA_API_URL = "http://localhost:11434/api/generate"


def _call_ollama(model_name: str, prompt: str, num_predict: int = 800) -> str:
    """
    Low-level helper to call Ollama and return the raw `response` text.
    """
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "num_predict": num_predict,
        "temperature": 0.7,
        "top_p": 0.9,
        "top_k": 40,
    }

    resp = requests.post(OLLAMA_API_URL, json=payload, timeout=600)
    resp.raise_for_status()
    data = resp.json()
    return data.get("response", "").strip()


def _extract_error_message(failure_text: str) -> str:
    """
    Pull the 'Error Message:' line out of the combined failure_text.
    """
    for line in failure_text.splitlines():
        if line.startswith("Error Message:"):
            return line.split("Error Message:", 1)[1].strip()
    return ""


def _extract_test_name(failure_text: str) -> str:
    for line in failure_text.splitlines():
        if line.startswith("Test Name:"):
            return line.split("Test Name:", 1)[1].strip()
    return ""


def _css_id_to_words(selector: str) -> str:
    """
    '#edit-profile-btn' -> 'Edit profile btn'
    """
    selector = selector.lstrip("#.")
    selector = selector.replace("-", " ").replace("_", " ").strip()
    if not selector:
        return "UI element"
    return selector.capitalize()


def _heuristic_bug_title(failure_text: str) -> str:
    """
    Generate a human-friendly bug title using simple rules,
    instead of trusting the LLM (which keeps copying full error_message).
    """
    error_msg = _extract_error_message(failure_text)
    test_name = _extract_test_name(failure_text)
    em_low = error_msg.lower()

    # 🔹 Playwright-specific assertion failures - detect BEFORE generic cleaning
    # toHaveTitle
    if "tohavetitle" in em_low or "to have title" in em_low:
        return "Page title does not match expected value"
    
    # toBeVisible
    if "tobevisible" in em_low or "to be visible" in em_low:
        if "button" in em_low:
            return "Expected button element is not visible"
        elif "input" in em_low:
            return "Expected input field is not visible"
        return "Expected UI element is not visible"
    
    # toHaveURL
    if "tohaveurl" in em_low or "to have url" in em_low:
        return "Page URL does not match expected value"
    
    # toHaveText
    if "tohavetext" in em_low or "to have text" in em_low:
        if "heading" in em_low or "h1" in em_low:
            return "Heading text does not match expected value"
        return "Element text content does not match expected value"
    
    # toHaveCount
    if "tohavecount" in em_low or "to have count" in em_low:
        if "paragraph" in em_low:
            return "Paragraph count does not match expected value"
        return "Element count does not match expected value"
    
    # toContainText
    if "tocontaintext" in em_low or "to contain text" in em_low:
        return "Element does not contain expected text"
    
    # toBeEnabled / toBeDisabled
    if "tobeenabled" in em_low or "to be enabled" in em_low:
        return "Element is not enabled as expected"
    if "tobedisabled" in em_low or "to be disabled" in em_low:
        return "Element is not disabled as expected"
    
    # toBeChecked
    if "tobechecked" in em_low or "to be checked" in em_low:
        return "Checkbox is not checked as expected"

    # Strip anything after 'Traceback' or long technical noise
    if "traceback" in em_low:
        error_msg = error_msg.split("Traceback", 1)[0].strip()
        em_low = error_msg.lower()

    # UI / NoSuchElement-style errors
    if "noselementexception" in em_low or "unable to locate element" in em_low:
        m = re.search(r"#([\w\-]+)", error_msg)
        if m:
            elem_name = _css_id_to_words("#" + m.group(1))
            return f"{elem_name} not found in UI"
        return "Required UI element not found on page"

    # React / JS / frontend TypeError
    if "cannot read properties of undefined" in em_low or "cannot read property" in em_low:
        return "Frontend component fails due to undefined value"

    # Database / timeout / psycopg2 errors
    if "psycopg2" in em_low or "database" in em_low or "connection timed out" in em_low:
        return "Database timeout while retrieving data"

    # 500 / internal server error-style failures
    if "internal server error" in em_low or "status code 500" in em_low or " 500" in em_low:
        if test_name:
            return f"Internal server error during {test_name}"
        return "Internal server error while processing request"

    # TypeError / attribute errors etc.
    if "typeerror" in em_low:
        return "Type error due to invalid input or state"
    if "attributeerror" in em_low:
        return "Attribute error accessing invalid or None object"

    # Generic assertion mismatch
    if "assertionerror" in em_low:
        return "Assertion failure in automated test"

    # Fallback: shorten the error message into a title-ish phrase
    if error_msg:
        # Remove the exception class if present
        if ":" in error_msg:
            _, after = error_msg.split(":", 1)
            core = after.strip()
        else:
            core = error_msg.strip()

        # 🔹 Clean out Playwright 'expect(...).toXxx(...) failed' noise if present
        core = re.sub(
            r"expect\(.*?\)\s*\.?\s*to\w+\(.*?\)\s*failed",
            "",
            core,
            flags=re.IGNORECASE,
        ).strip()

        # If cleaning removed everything, fall back to a generic title
        if not core:
            return "Assertion failure in automated UI test"

        # Take only a limited number of words
        words = core.split()
        shortened = " ".join(words[:10])
        return shortened[:120].rstrip(" :,-")

    # Ultimate fallback
    return "Automated test failure"


def _sanitize_description(bug_description: str, failure_text: str) -> str:
    """
    Remove raw lines that just repeat the failure text (Test Name, Stack Trace, Logs, etc),
    so the description looks like a clean explanation, not a dump.
    """
    failure_lines = {
        line.strip() for line in failure_text.splitlines() if line.strip()
    }

    cleaned_lines = []
    for line in bug_description.splitlines():
        stripped = line.strip()
        lower = stripped.lower()

        if not stripped:
            cleaned_lines.append("")
            continue

        # Remove exact failure lines
        if stripped in failure_lines:
            continue

        # Remove obvious technical dump patterns
        if stripped.startswith("Test Name:"):
            continue
        if stripped.startswith("File Path:"):
            continue
        if stripped.startswith("Error Message:"):
            continue
        if stripped.startswith("Stack Trace:"):
            continue
        if stripped.startswith("Logs:"):
            continue
        if "traceback (most recent call last):" in lower:
            continue
        if stripped.startswith("Traceback (most recent call last):"):
            continue
        if "file \"" in lower and " line " in lower and " in " in lower:
            continue
        if stripped.startswith("[") and "]" in stripped and ("error" in lower or "debug" in lower):
            continue

        cleaned_lines.append(stripped)

    # Collapse multiple blank lines
    final_lines = []
    prev_blank = False
    for line in cleaned_lines:
        if line == "":
            if not prev_blank:
                final_lines.append("")
            prev_blank = True
        else:
            final_lines.append(line)
            prev_blank = False

    return "\n".join(final_lines).strip()


def generate_bug_report(model_name: str, failure_text: str) -> dict:
    """
    - Title: generated heuristically from the error message.
    - Description: generated by LLM, then cleaned to avoid raw dumps.
    """
    import os
    
    # Override model_name with environment variable if available
    # This ensures we use the correct Ollama model from .env.local
    model_name = os.getenv("OLLAMA_MODEL", model_name or "llama3.2:3b")

    # 1) TITLE (heuristic)
    bug_title = _heuristic_bug_title(failure_text)

    # 2) DESCRIPTION (LLM)
    desc_prompt = f"""
You are an expert QA engineer.

Read the FAILED TEST DETAILS below and write a long, detailed, professional bug description
that will help developers quickly understand and fix the issue.

Write in full sentences and natural language, as if writing in a real bug tracking system.

VERY IMPORTANT FORMAT RULES:
- Do NOT paste or repeat the exact raw stack trace.
- Do NOT paste or repeat the exact raw log lines.
- Do NOT just copy the error message.
- Instead, explain them in your own words.

Content requirements:
- Around 160–220 words.
- 3–5 clear paragraphs separated by blank lines.
- Start with a one-sentence summary of the failure.
- Explain the expected behaviour vs the actual behaviour.
- Mention where it likely happens (UI, API endpoint, backend service, database, etc.).
- Suggest a likely root cause using the error message, stack trace and logs.
- Explain the impact on users or the system.
- Describe how the failure appeared during test execution (what the test was trying to validate).
- End with a short suggestion of what the development team should investigate or fix.

FAILED TEST DETAILS:
{failure_text}
"""

    try:
        bug_description = _call_ollama(model_name, desc_prompt, num_predict=1200)
    except Exception as e:
        # Raise so triage_service can fallback
        raise e

    bug_description = _sanitize_description(bug_description, failure_text)

    return {
        "title": bug_title,
        "description": bug_description.strip(),
    }
