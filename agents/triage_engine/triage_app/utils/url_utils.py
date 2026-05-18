"""
URL utility functions for the bug triage engine.

This module provides utilities for converting file paths to clickable file:// URLs
that can be used in IDEs, terminals, and browsers.
"""

import os
from typing import Optional
from urllib.parse import quote


def convert_path_to_url(file_path: str) -> str:
    """
    Convert a file path to a clickable file:// URL.
    
    Args:
        file_path: The file path to convert (can be absolute or relative)
    
    Returns:
        A properly formatted file:// URL
        
    Examples:
        >>> convert_path_to_url("demo.spec.js")
        'file:///C:/bug-triage-engine/demo.spec.js'
        
        >>> convert_path_to_url("c:\\tests\\login.spec.js")
        'file:///c:/tests/login.spec.js'
    """
    if not file_path:
        return ""
    
    # Convert to absolute path if it's relative
    abs_path = os.path.abspath(file_path)
    
    # Normalize path separators (convert backslashes to forward slashes)
    normalized_path = abs_path.replace('\\', '/')
    
    # URL encode the path to handle special characters
    encoded_path = quote(normalized_path, safe='/:')
    
    # Format as file:// URL (triple slash for absolute paths on Windows)
    # On Windows, paths like C:/... need to be file:///C:/...
    if encoded_path.startswith('/'):
        return f"file://{encoded_path}"
    else:
        return f"file:///{encoded_path}"


def format_file_url_with_line(file_path: str, line_number: Optional[int] = None) -> str:
    """
    Convert a file path to a clickable file:// URL with optional line number anchor.
    
    This creates URLs that can be clicked in VS Code and other IDEs to jump directly
    to the specified line number.
    
    Args:
        file_path: The file path to convert (can be absolute or relative)
        line_number: Optional line number to include as an anchor (e.g., #L123)
    
    Returns:
        A properly formatted file:// URL with line number anchor if provided
        
    Examples:
        >>> format_file_url_with_line("demo.spec.js", 42)
        'file:///C:/bug-triage-engine/demo.spec.js#L42'
        
        >>> format_file_url_with_line("test.py")
        'file:///C:/bug-triage-engine/test.py'
    """
    if not file_path:
        return ""
    
    # Get the base URL
    base_url = convert_path_to_url(file_path)
    
    # Add line number anchor if provided
    if line_number is not None and line_number > 0:
        return f"{base_url}#L{line_number}"
    
    return base_url


def validate_file_path(file_path: str) -> bool:
    """
    Validate if a file path exists and is accessible.
    
    Args:
        file_path: The file path to validate
    
    Returns:
        True if the file exists and is accessible, False otherwise
    """
    if not file_path:
        return False
    
    try:
        return os.path.isfile(file_path)
    except (OSError, ValueError):
        return False


def extract_test_url_from_logs(logs: str) -> Optional[str]:
    """
    Extract the test URL (http/https) from log text.
    
    Prioritizes URLs that appear after navigation-related keywords like
    "Navigating to", "Opening", "URL:", etc.
    
    Args:
        logs: The log text to extract URL from
    
    Returns:
        The first valid HTTP/HTTPS URL found, or None if no URL is found
        
    Examples:
        >>> extract_test_url_from_logs("[2025-12-13 15:30:16] DEBUG: Navigating to https://example.com/login")
        'https://example.com/login'
        
        >>> extract_test_url_from_logs("Opening URL: http://localhost:3000/dashboard")
        'http://localhost:3000/dashboard'
    """
    if not logs:
        return None
    
    import re
    
    # Priority 1: Look for URLs after navigation keywords
    navigation_patterns = [
        r'Navigating to\s+(https?://[^\s\]]+)',
        r'Opening\s+(https?://[^\s\]]+)',
        r'URL:\s+(https?://[^\s\]]+)',
        r'Visiting\s+(https?://[^\s\]]+)',
        r'Loading\s+(https?://[^\s\]]+)',
        r'Navigate to\s+(https?://[^\s\]]+)',
    ]
    
    for pattern in navigation_patterns:
        match = re.search(pattern, logs, re.IGNORECASE)
        if match:
            return match.group(1).rstrip('.,;')
    
    # Priority 2: Look for any http/https URL in the logs
    url_match = re.search(r'(https?://[^\s\]]+)', logs)
    if url_match:
        return url_match.group(1).rstrip('.,;')
    
    return None
