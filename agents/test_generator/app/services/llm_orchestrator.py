"""LLM Orchestrator service with fallback logic."""
import json
from typing import Dict, Any
from app.services.multi_llm_client import LLMClient
from app.core.logger import app_logger
from app.core.config import settings


# ============================================================================
# PROMPT TEMPLATE
# ============================================================================
PROMPT_TEMPLATE = """
You are a Senior SDET (Software Development Engineer in Test) with expertise in Playwright and Semantic Test Automation.

Your Goal: Analyze a list of UI locators (JSON) and generate robust, logical, and independent test cases.

CRITICAL INSTRUCTION:
DO NOT generate a single "Click-Fest" test that clicks every element blindly.
Instead, GROUP locators into logical scenarios and generate SEPARATE test cases for each group.

STRATEGY:
1.  **Analyze**: Group locators by functionality:
    *   **Navigation**: Links in headers/sidebars that go to new pages.
    *   **Authentication**: Login/Sign-up forms (Inputs + Submit).
    *   **Content verification**: Headings, text blobs, images (Read-only).
    *   **Interactions**: Search bars, filters, toggles (State changes).
2.  **Isolate**: Create ONE test case per logical group.
    *   *Example*: "TC_Global_Nav" (Test all header links).
    *   *Example*: "TC_Login_Flow" (Test email/password inputs).
    *   *Example*: "TC_Hero_Content" (Verify main page text).

RULES FOR STEPS:
1.  **State Awareness**: If you click a Link ("Site Nav", "Login"), the VERY NEXT STEP must be a Verification (e.g., "Verify URL contains '/login'").
2.  **Stop on Navigation**: If a test case involves clicking a link that navigates away, that test case MUST END immediately after the URL verification. DO NOT try to click footer elements *after* navigating to a new page.
3.  **Positive Verification**: After every ACTION (Click/Type), add a VERIFICATION (Check visible/Check URL).
4.  **Selection**: Do NOT use every locator. Use only the ones relevant to the specific test scenario.

OUTPUT FORMAT (JSON ONLY):
{
  "<page_name>": {
    "url": "<PAGE_URL>",
    "testCases": [
      {
        "id": "TC_<Functionality>_<Number>",
        "title": "Verify <Specific Functionality>",
        "url": "<CURRENT_PAGE_URL>",
        "inputs": {
            "ID_OF_LOCATOR_FROM_JSON": "Actual Input Value"
        },
        "steps": [
          "Navigate to <URL>",
          "Enter 'Actual Input Value' into the field",
          "Click the 'Submit' locator"
        ],
        "expected": [
          "Success message is displayed"
        ]
      }
    ]
  }
}

CRITICAL RULES FOR INPUTS (MANDATORY):
1. INPUT KEYS: The keys in the "inputs" dictionary MUST be the exact keys from the LOCATORS JSON provided to you (e.g., "state_1_input_email_487_298"). Do NOT use generic names like "first_name".
2. INPUT VALUES: The values in the "inputs" dictionary MUST be realistic strings (e.g., "John Doe", "user@example.com").
3. NO MOCK IDS IN VALUES: Never use locator IDs as the values; they must be the keys.

INPUT
INPUT_CONTEXT_LABEL_PLACEHOLDER
INPUT_CONTEXT_DATA_PLACEHOLDER
"""


class LLMOrchestratorService:
    """Orchestrates LLM calls using the unified LLMClient."""
    
    def __init__(self):
        self.llm_client = LLMClient()
    
    async def generate_test_cases(
        self, 
        code_content: str
    ) -> tuple[Dict[str, Any], str]:
        """
        Generate test cases using LLMClient (handles multi-provider fallback internally).
        """
        app_logger.info("Generating test cases using LLMClient...")
        
        # Prepare prompt context
        input_context_label = "Python Code"
        input_context_data = code_content
        code_dict = {"code": code_content}

        try:
            response = await self.llm_client.generate_test_cases(
                requirements=code_dict,
                prompt_template=PROMPT_TEMPLATE,
                input_context_label=input_context_label,
                input_context_data=input_context_data
            )
            
            # Normalize response
            normalized_response = self._normalize_response(response)
            
            # Log success
            page_keys = [k for k in normalized_response.keys() if k != "testCases" and isinstance(normalized_response.get(k), dict)]
            app_logger.info(f"Successfully generated test cases. Page keys: {page_keys}")
            
            # Determine model label
            model_used = settings.openrouter_model if settings.openrouter_api_key else (settings.huggingface_model or "unknown")
            return normalized_response, model_used

        except Exception as e:
            app_logger.error(f"Test case generation failed: {e}")
            raise

    def _normalize_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize LLM response to ALWAYS return page names as keys format.
        Handles page names as keys format, pages array format, and flat array format.
        
        Args:
            response: Raw response from LLM
            
        Returns:
            Normalized response with pages as keys (page names), and flat testCases array
        """
        all_test_cases = []
        pages_by_name = {}
        metadata_keys = {"pages", "test_cases", "testCases", "totalTestCases", "generatedAt", "modelUsed", "filename"}
        
        # Step 1: Check if response already uses page names as keys (new format: {"page_name": {...}, ...})
        if isinstance(response, dict):
            # Check if any key (that's not metadata) has a dict value with url/testCases
            has_page_names_format = False
            for key, value in response.items():
                if key not in metadata_keys and isinstance(value, dict):
                    if "url" in value or "testCases" in value or "test_cases" in value:
                        has_page_names_format = True
                        break
            
            if has_page_names_format:
                # IMPORTANT: When page names format is detected, IGNORE root-level testCases/test_cases
                # to avoid duplicates. We'll build testCases array only from the pages.
                # Format: {"page_name": {"url": "...", "testCases": [...]}, ...}
                app_logger.debug("Detected page names as keys format in LLM response")
                
                # Check if root-level testCases exists (might be duplicate)
                root_test_cases = response.get("testCases") or response.get("test_cases")
                if root_test_cases:
                    app_logger.debug(f"Found root-level testCases with {len(root_test_cases) if isinstance(root_test_cases, list) else 'unknown'} items - will ignore to avoid duplicates")
                
                for page_name, page_data in response.items():
                    # Skip metadata keys (including root-level testCases/test_cases to avoid duplicates)
                    if page_name in metadata_keys:
                        continue
                    
                    if not isinstance(page_data, dict):
                        continue
                    
                    # Get URL from page data
                    page_url = page_data.get("url") or page_data.get("pageUrl") or page_data.get("page_url") or ""
                    
                    # Get test cases for this page
                    page_test_cases = page_data.get("testCases") or page_data.get("test_cases") or []
                    
                    # Normalize each test case in this page
                    normalized_page_cases = []
                    for case in page_test_cases:
                        normalized_case = self._normalize_test_case(case, page_url)
                        normalized_page_cases.append(normalized_case)
                        all_test_cases.append(normalized_case)
                    
                    # Store page with normalized test cases (keep original page name)
                    pages_by_name[page_name] = {
                        "url": page_url,
                        "testCases": normalized_page_cases
                    }
                
                # Return with page names as keys
                # IMPORTANT: Only include flat testCases array built from pages, NOT root-level testCases
                # This ensures no duplicates even if LLM returned both formats
                result = {**pages_by_name}
                result["testCases"] = all_test_cases  # Use ONLY the normalized test cases from pages
                app_logger.debug(f"Normalized response with page names: {list(pages_by_name.keys())}")
                app_logger.debug(f"Total test cases after normalization (from pages only): {len(all_test_cases)}")
                return result
        
        # Step 2: Check if response is grouped by pages array (old format: {"pages": [...]})
        if "pages" in response:
            app_logger.debug("Detected pages array format in LLM response, converting to page names as keys")
            pages_data = response["pages"]
            
            for page in pages_data:
                # Get URL from page
                page_url = page.get("url") or page.get("pageUrl") or page.get("page_url") or ""
                
                # Get test cases for this page first (to extract module name)
                page_test_cases = page.get("testCases") or page.get("test_cases") or []
                
                # Get page name - prefer module name from first test case, then URL, then explicit name
                page_name = None
                if page_test_cases and isinstance(page_test_cases[0], dict):
                    # Use module name from first test case (most reliable)
                    page_name = page_test_cases[0].get("module", "")
                
                if not page_name:
                    # Try explicit page name field
                    page_name = page.get("name") or page.get("pageName") or page.get("page_name")
                
                if not page_name and page_url:
                    # Infer from URL (e.g., "/page-name" -> "page-name", "https://example.com/page" -> "page")
                    url_parts = page_url.rstrip('/').split('/')
                    page_name = url_parts[-1] if url_parts and url_parts[-1] else "unknown"
                
                if not page_name:
                    page_name = "unknown"
                
                # Normalize page name (lowercase, keep underscores/hyphens, but normalize spaces)
                page_name = page_name.lower().replace(" ", "_")
                
                # Normalize each test case in this page
                normalized_page_cases = []
                for case in page_test_cases:
                    normalized_case = self._normalize_test_case(case, page_url)
                    normalized_page_cases.append(normalized_case)
                    all_test_cases.append(normalized_case)
                
                # Store page with normalized test cases
                pages_by_name[page_name] = {
                    "url": page_url,
                    "testCases": normalized_page_cases
                }
            
            # Return with page names as keys
            result = {**pages_by_name}
            result["testCases"] = all_test_cases  # Also include flat array for backward compatibility
            app_logger.debug(f"Converted pages array to page names: {list(pages_by_name.keys())}")
            return result
        
        # Step 3: Handle old flat format (backward compatibility)
        app_logger.debug("Detected flat array format in LLM response, converting to page names as keys")
        test_cases_data = None
        if "test_cases" in response:
            test_cases_data = response["test_cases"]
        elif "testCases" in response:
            test_cases_data = response["testCases"]
        else:
            app_logger.warning("Response missing page keys, 'pages', 'test_cases' or 'testCases' key, attempting to wrap")
            if isinstance(response, list):
                test_cases_data = response
            else:
                test_cases_data = [response] if response else []
        
        # Normalize each test case (old format)
        normalized_cases = []
        for case in test_cases_data:
            normalized_case = self._normalize_test_case(case, None)
            normalized_cases.append(normalized_case)
            all_test_cases.append(normalized_case)
        
        # Group by module name to create page groups (use module name as page key)
        module_groups = {}
        for case in normalized_cases:
            # Use module name as page name (normalize it)
            module_name = case.get("module", "unknown").lower().replace(" ", "_")
            url = case.get("url", "/unknown")
            
            if module_name not in module_groups:
                module_groups[module_name] = {
                    "url": url,
                    "testCases": []
                }
            module_groups[module_name]["testCases"].append(case)
        
        # Return with page names as keys
        result = {**module_groups}
        result["testCases"] = all_test_cases  # Also include flat array for backward compatibility
        app_logger.debug(f"Converted flat array to page names: {list(module_groups.keys())}")
        return result
    
    def _normalize_test_case(self, case: Dict[str, Any], page_url: str = None) -> Dict[str, Any]:
        """
        Normalize a single test case.
        
        Args:
            case: Raw test case data
            page_url: URL from page group (if available)
            
        Returns:
            Normalized test case
        """
        normalized_case = {}
        
        # Required fields - map from various possible names
        normalized_case["id"] = case.get("id") or case.get("test_case_id") or f"TC-{hash(str(case)) % 10000:04d}"
        normalized_case["title"] = case.get("title") or case.get("name") or "Untitled Test Case"
        
        # URL - use page_url if provided, otherwise extract from case
        url = page_url or case.get("url") or case.get("page_url") or case.get("path") or ""
        normalized_case["url"] = url
        
        # Inputs - ensure it's a dict
        inputs = case.get("inputs") or case.get("input") or case.get("testData") or {}
        normalized_case["inputs"] = inputs if isinstance(inputs, dict) else {}
        
        # Steps - ensure it's a list
        steps = case.get("steps") or case.get("test_steps") or []
        normalized_case["steps"] = steps if isinstance(steps, list) else []
        
        # Expected - ensure it's a list, handle both array and string
        expected = case.get("expected") or case.get("expectedResult") or case.get("expected_result") or []
        if isinstance(expected, str):
            normalized_case["expected"] = [expected]
        elif isinstance(expected, list):
            normalized_case["expected"] = expected
        else:
            normalized_case["expected"] = []
        
        return normalized_case
