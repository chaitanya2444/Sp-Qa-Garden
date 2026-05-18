"""
Intelligent Playwright error label detection service.
Uses BERT model for classification with pattern-based fallback.
"""

import re
import requests
from typing import Optional


def _call_bert_classifier(text: str, bert_url: str, candidate_labels: list) -> str:
    """
    Call BERT server to classify error text into one of the candidate labels.
    
    Args:
        text: Error text to classify
        bert_url: BERT server endpoint URL
        candidate_labels: List of possible labels
        
    Returns:
        Best matching label from BERT classification
    """
    try:
        # Use the /predict endpoint
        endpoint = bert_url.replace("/triage", "/predict")
        
        payload = {
            "text": text,
            "labels": candidate_labels
        }
        
        response = requests.post(endpoint, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        return result.get("label", candidate_labels[0])
        
    except Exception as e:
        # Fallback to first label if BERT fails
        print(f"BERT classification failed: {e}")
        return candidate_labels[0] if candidate_labels else "Test Failure"


def _detect_playwright_assertion_type(error_message: str) -> Optional[str]:
    """
    Detect specific Playwright assertion type from error message.
    Returns specific label if assertion is detected, None otherwise.
    """
    em_low = error_message.lower()
    
    # Playwright assertion patterns
    if "tohavetitle" in em_low or "to have title" in em_low:
        return "Assertion: Title Mismatch"
    
    if "tobevisible" in em_low or "to be visible" in em_low:
        return "Assertion: Element Not Visible"
    
    if "tohaveurl" in em_low or "to have url" in em_low:
        return "Assertion: URL Mismatch"
    
    if "tohavetext" in em_low or "to have text" in em_low:
        return "Assertion: Text Mismatch"
    
    if "tohavecount" in em_low or "to have count" in em_low:
        return "Assertion: Count Mismatch"
    
    if "tocontaintext" in em_low or "to contain text" in em_low:
        return "Assertion: Missing Text"
    
    if "tobeenabled" in em_low or "to be enabled" in em_low:
        return "Assertion: Element Not Enabled"
    
    if "tobedisabled" in em_low or "to be disabled" in em_low:
        return "Assertion: Element Not Disabled"
    
    if "tobechecked" in em_low or "to be checked" in em_low:
        return "Assertion: Checkbox Not Checked"
    
    if "tohavevalue" in em_low or "to have value" in em_low:
        return "Assertion: Value Mismatch"
    
    if "tohaveattribute" in em_low or "to have attribute" in em_low:
        return "Assertion: Attribute Mismatch"
    
    if "tobeattached" in em_low or "to be attached" in em_low:
        return "Assertion: Element Not Attached"
    
    return None


def _get_candidate_labels_from_patterns(error_message: str, stack_trace: str) -> list:
    """
    Generate candidate labels based on error patterns.
    These will be used for BERT classification.
    """
    combined_text = f"{error_message} {stack_trace}".lower()
    candidates = []
    
    # Timeout patterns
    if "timeout" in combined_text or "timed out" in combined_text:
        candidates.append("Timeout Error")
    
    # Element locator issues
    if "locator" in combined_text or "selector" in combined_text:
        candidates.append("Element Locator Issue")
    
    # Element not found
    if "not found" in combined_text or "unable to locate" in combined_text:
        candidates.append("Element Not Found")
    
    # Navigation issues
    if "navigation" in combined_text or "goto" in combined_text:
        candidates.append("Navigation Error")
    
    # Network/API issues
    if "network" in combined_text or "request failed" in combined_text or "api" in combined_text:
        candidates.append("Network Error")
    
    # Screenshot/video issues
    if "screenshot" in combined_text or "video" in combined_text:
        candidates.append("Media Capture Error")
    
    # Action failures (click, type, etc.)
    if "click" in combined_text:
        candidates.append("Click Action Failed")
    if "type" in combined_text or "fill" in combined_text:
        candidates.append("Input Action Failed")
    if "hover" in combined_text:
        candidates.append("Hover Action Failed")
    
    # Assertion failures (generic)
    if "expect" in combined_text or "assertion" in combined_text:
        candidates.append("Assertion Failure")
    
    # Page/frame issues
    if "frame" in combined_text:
        candidates.append("Frame Error")
    if "page closed" in combined_text or "page crashed" in combined_text:
        candidates.append("Page Crash")
    
    # If no specific patterns found, add generic labels
    if not candidates:
        candidates = [
            "Test Failure",
            "UI Test Error",
            "Playwright Error"
        ]
    
    return candidates


def detect_playwright_label(
    error_message: str,
    stack_trace: str,
    failure_text: str,
    bert_url: Optional[str] = None
) -> str:
    """
    Intelligently detect triage label for Playwright errors using BERT prominently.
    
    NEW APPROACH - BERT-First Classification:
    1. Generate ALL possible candidate labels (assertions + patterns)
    2. Use BERT to classify among ALL candidates (uses 30K trained model)
    3. Falls back to pattern-based detection only if BERT unavailable
    
    This ensures BERT is used for ALL errors, not just non-assertion ones.
    
    Args:
        error_message: The error message from test failure
        stack_trace: The stack trace from test failure
        failure_text: Complete failure text
        bert_url: Optional BERT server URL for classification
        
    Returns:
        Intelligent triage label string
    """
    # Step 1: Build comprehensive candidate list
    candidates = []
    
    # Add assertion-specific labels if detected
    assertion_label = _detect_playwright_assertion_type(error_message)
    if assertion_label:
        candidates.append(assertion_label)
    
    # Add pattern-based candidates
    pattern_candidates = _get_candidate_labels_from_patterns(error_message, stack_trace)
    candidates.extend(pattern_candidates)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_candidates = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique_candidates.append(c)
    
    candidates = unique_candidates if unique_candidates else ["Test Failure"]
    
    # Step 2: Use BERT for classification (PRIMARY METHOD)
    if bert_url:
        # Combine error info for BERT analysis
        text_for_classification = f"{error_message}\n{stack_trace[:500]}"
        bert_label = _call_bert_classifier(text_for_classification, bert_url, candidates)
        return bert_label
    
    # Step 3: Fallback - return the first (most specific) candidate only if BERT unavailable
    return candidates[0]
