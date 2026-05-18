import os
import sys
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv
load_dotenv()
import json

# =========================
# CONFIG
# =========================
load_dotenv()

# Multi-Provider Configuration
XAI_KEY = os.getenv("XAI_API_KEY")
XAI_MODEL = os.getenv("XAI_MODEL", "grok-beta")
XAI_URL = os.getenv("XAI_BASE_URL", "https://api.x.ai/v1")

GRO_KEYS = [k.strip() for k in os.getenv("GROQ_API_KEYS", "").split(",") if k.strip()]
if not GRO_KEYS and os.getenv("GROQ_API_KEY"):
    GRO_KEYS = [os.getenv("GROQ_API_KEY")]

GROQ_CURRENT_KEY_INDEX = 0
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

OR_KEY = os.getenv("OPENROUTER_API_KEY")
OR_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-405b-instruct") 
OR_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

HF_KEY = os.getenv("HUGGINGFACE_API_KEY")
HF_MODEL = os.getenv("HUGGINGFACE_MODEL", "meta-llama/Meta-Llama-3.1-8B-Instruct")

PROJECT_ROOT = Path(__file__).resolve().parent
PROMPT_FILE = PROJECT_ROOT / "prompt.txt"

CONFIG_DIR = PROJECT_ROOT / "config"
TESTCASES_DIR = PROJECT_ROOT / "testcases"
OUTPUT_TESTS_DIR = PROJECT_ROOT / "tests"

OUTPUT_TESTS_DIR.mkdir(exist_ok=True)

# =========================
# UTILITIES
# =========================
def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""

def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def inject_pythonpath(code: str) -> str:
    injection = (
        "import sys\n"
        "from pathlib import Path\n"
        "ROOT_DIR = Path(__file__).resolve().parent.parent.parent\n"
        "sys.path.insert(0, str(ROOT_DIR))\n\n"
    )
    return injection + code

# =========================
# LLM INTEGRATION (MULTI-PROVIDER)
# =========================
def call_llm(prompt: str) -> str:
    """Call LLM with Grok -> Groq (Rotating) -> OpenRouter -> Hugging Face fallback."""
    global GROQ_CURRENT_KEY_INDEX

    # 1. Try Grok (xAI)
    if XAI_KEY and "your_" not in XAI_KEY:
        try:
            return _call_xai(prompt)
        except Exception as e:
            print(f"Grok (xAI) failed: {e}. Falling back...")

    # 2. Try Groq (High Speed with Key Rotation)
    if GRO_KEYS:
        for i in range(len(GRO_KEYS)):
            idx = (GROQ_CURRENT_KEY_INDEX + i) % len(GRO_KEYS)
            key = GRO_KEYS[idx]
            try:
                res = _call_groq(prompt, key)
                GROQ_CURRENT_KEY_INDEX = (idx + 1) % len(GRO_KEYS)
                return res
            except Exception as e:
                if "429" in str(e) and i < len(GRO_KEYS) - 1:
                    print(f"Groq key {idx+1} rate limited. Rotating...")
                    continue
                print(f"Groq failed: {e}. Falling back...")
                break

    # 3. Try OpenRouter
    if OR_KEY:
        try:
            return _call_openrouter(prompt)
        except Exception as e:
            print(f"OpenRouter failed: {e}. Falling back...")

    # 4. Try Hugging Face
    if HF_KEY:
        try:
            return _call_huggingface(prompt)
        except Exception as e:
            print(f"Hugging Face failed: {e}")

    raise RuntimeError("All LLM providers failed")

def _call_xai(prompt: str) -> str:
    import httpx
    url = f"{XAI_URL}/chat/completions"
    headers = {"Authorization": f"Bearer {XAI_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": XAI_MODEL,
        "messages": [
            {"role": "system", "content": "You are an expert Playwright test automation engineer."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }
    with httpx.Client(timeout=60.0) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']

def _call_groq(prompt: str, api_key: str) -> str:
    from groq import Groq
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": "You are an expert Playwright test automation engineer."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
    )
    return response.choices[0].message.content.strip()

def _call_openrouter(prompt: str) -> str:
    import httpx
    url = f"{OR_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {OR_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://qa-garden.com",
        "X-Title": "QA Garden CICD"
    }
    payload = {
        "model": OR_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }
    with httpx.Client(timeout=60.0) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']

def _call_huggingface(prompt: str) -> str:
    import httpx
    url = "https://router.huggingface.co/hf-inference"
    headers = {"Authorization": f"Bearer {HF_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": HF_MODEL,
        "inputs": prompt,
        "parameters": {"max_new_tokens": 4096, "temperature": 0.1}
    }
    with httpx.Client(timeout=120.0) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        if isinstance(result, list) and len(result) > 0:
            return result[0].get('generated_text', '')
        return result.get('generated_text', '')

def extract_code_only(text: str) -> str:
    """Extract Python code from LLM response"""
    # Handle code blocks
    if "```python" in text:
        code = text.split("```python")[1].split("```")[0].strip()
        return code
    elif "```" in text:
        code = text.split("```")[1].split("```")[0].strip()
        return code
    
    # Handle custom tags
    if "<BEGIN_CODE>" in text and "<END_CODE>" in text:
        code = text.split("<BEGIN_CODE>")[1].split("<END_CODE>")[0].strip()
        import html
        return html.unescape(code)
    
    # Return as-is if it looks like Python code
    stripped = text.strip()
    if stripped.startswith(("import ", "from ", "def ", "class ")):
        return stripped
    
    raise RuntimeError("Could not extract Python code from LLM response")
def generate_page_tests_fallback(page: str):
    """Fallback direct generation if LLM fails"""
    raw_testcase_code = read_file(TESTCASES_DIR / f"{page}_testcases.json")
    
    if not raw_testcase_code:
        return
    
    try:
        data = json.loads(raw_testcase_code)
        test_cases = data.get('testCases', [])
        
        if not test_cases:
            return
        
        # Generate test code directly from JSON inputs
        test_code = generate_imports(page)
        
        for test_case in test_cases:
            test_code += generate_test_from_inputs(test_case, page)
        
        # Apply minimal post-processing
        test_code = inject_pythonpath(test_code)
        test_code = fix_locator_usage(test_code)
        
        # Write fallback file
        test_dir = OUTPUT_TESTS_DIR / page
        out_path = test_dir / f"test_{page}.py"
        write_file(out_path, test_code)
        
        print(f"Generated fallback {out_path.name} for {page}")
        
    except Exception as e:
        print(f"Fallback generation also failed for {page}: {e}")

def generate_test_from_inputs(test_case: dict, page: str) -> str:
    """Generate individual test function using test case data"""
    test_id = test_case.get('id', '')
    title = test_case.get('title', '')
    inputs = test_case.get('inputs', {})
    steps = test_case.get('steps', [])
    expected = test_case.get('expected', [])
    
    # Convert test ID to function name
    func_name = test_id.lower().replace('_tc_', '_').replace('tc_', '')
    
    # Determine fixture type
    fixture = 'authenticated_page' if page == 'welcome' else 'page'
    
    # Generate test function with docstring
    test_code = f"def test_{func_name}({fixture}):\n"
    if title:
        test_code += f'    """Test: {title}"""\n'
    
    # Add navigation for non-welcome pages
    if page != 'welcome':
        url_var = f"{page.upper()}_URL"
        test_code += f"    {fixture}.goto({url_var}, timeout=60000)\n"
        test_code += f"    {fixture}.wait_for_load_state('networkidle')\n"
    
    # Generate test steps based on inputs
    locator_class = get_locator_class(page)
    
    # Process inputs
    for key, value in inputs.items():
        if key.endswith('_locator'):
            field_name = key.replace('_locator', '')
            if field_name in inputs:
                locator_ref = value.replace(f'{locator_class}.', '')
                test_code += f"    {fixture}.locator({locator_class}.{locator_ref}).fill('{inputs[field_name]}')\n"
        elif key.endswith(('_button', '_link', '_toggle')):
            locator_ref = value.replace(f'{locator_class}.', '')
            test_code += f"    {fixture}.locator({locator_class}.{locator_ref}).click()\n"
            test_code += f"    {fixture}.wait_for_load_state('networkidle')\n"
    
    # Handle confirm_password separately for signup
    if page == 'signup' and 'confirm_password' in inputs and 'confirm_password_locator' in inputs:
        locator_ref = inputs['confirm_password_locator'].replace(f'{locator_class}.', '')
        test_code += f"    {fixture}.locator({locator_class}.{locator_ref}).fill('{inputs['confirm_password']}')\n"
    
    # Add assertions based on test case expectations if provided
    if expected:
        for exp in expected:
            # Simple heuristic for common assertions
            if "visible" in exp.lower() or "display" in exp.lower():
                # Try to find a locator for an element mentioned in the expectation
                pass 
    
    # Generic fail-safe: add a visible check for any primary element
    if inputs:
        first_key = list(inputs.keys())[0]
        if "_locator" in first_key:
            locator_ref = inputs[first_key].replace(f'{locator_class}.', '')
            test_code += f"    expect({fixture}.locator({locator_class}.{locator_ref})).to_be_visible()\n"
    
    return test_code + "\n"
    
    return test_code + "\n"

def get_locator_class(page: str) -> str:
    """Get the appropriate locator class for the page"""
    page_clean = page.replace(" ", "_").replace("-", "_").lower()
    mapping = {
        'login': 'LoginLocators',
        'signup': 'SignupLocators', 
        'welcome': 'WelcomeLocators'
    }
    if page_clean in mapping:
        return mapping[page_clean]
    
    # Dynamic class name generation
    return "".join([word.capitalize() for word in page_clean.split("_")]) + "Locators"

def generate_imports(page: str) -> str:
    """Generate appropriate imports for the page"""
    locator_class = get_locator_class(page)
    module_name = f"{page}_locators"
    
    imports = [
        "import sys",
        "from pathlib import Path", 
        "ROOT_DIR = Path(__file__).resolve().parent.parent",
        "sys.path.insert(0, str(ROOT_DIR))",
        "",
        f"from config.{module_name} import {locator_class}",
        "from playwright.sync_api import expect"
    ]
    
    if page != 'welcome':
        imports.insert(-1, f"from config.urls import {page.upper()}_URL")
    
    return "\n".join(imports) + "\n\n"

def fix_locator_usage(code: str) -> str:
    """Fix locator usage patterns"""
    import re
    
    # Fix expect patterns for visibility
    code = re.sub(r'expect\(page\.locator\(([^)]+)\)\)\.be_visible\(\)', r'expect(page.locator(\1)).to_be_visible()', code)
    code = re.sub(r'expect\(page\.locator\(([^)]+)\)\)\.to_have_js_property', r'expect(page.locator(\1)).to_have_js_property', code)
    
    # Remove any remaining 'await' keywords
    code = re.sub(r'\bawait\s+', '', code)
    
    return code

# =========================
# PAGE DISCOVERY
# =========================
def infer_pages():
    pages = []
    for tc_file in TESTCASES_DIR.glob("*_testcases.json"):
        page = tc_file.stem.replace("_testcases", "")
        locator_file = CONFIG_DIR / f"{page}_locators.py"
        if locator_file.exists():
            pages.append(page)
    return pages

# =========================
# GENERATE conftest.py
# =========================
def generate_conftest():
    content = """
import sys
from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright
import logging
import datetime
import shutil
import time
import threading
import requests
import os
import json

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()

@pytest.fixture
def context(browser, request):
    # Extract page type from test file path
    test_file = request.node.fspath.basename
    page_type = test_file.replace("test_", "").replace(".py", "")
    test_name = request.node.name
    
    # Create artifacts directory structure
    artifacts_dir = Path("artifacts")
    
    # Organized subdirectories
    videos_dir = artifacts_dir / "videos" / page_type
    traces_dir = artifacts_dir / "traces" / page_type
    videos_dir.mkdir(parents=True, exist_ok=True)
    traces_dir.mkdir(parents=True, exist_ok=True)
    
    # Clean up existing artifacts for this test
    for old_file in videos_dir.glob(f"{test_name}.*"):
        old_file.unlink(missing_ok=True)
    
    context = browser.new_context(record_video_dir=str(videos_dir))
    context.tracing.start(screenshots=True, snapshots=True)
    yield context
    context.tracing.stop(path=str(traces_dir / f"{test_name}.zip"))
    
    context.close()
    
    # Rename video file to match test name
    try:
        video_files = list(videos_dir.glob("*.webm"))
        if video_files:
            video_files.sort(key=os.path.getmtime, reverse=True)
            old_video = video_files[0]
            new_video = videos_dir / f"{test_name}.webm"
            if new_video.exists(): new_video.unlink()
            old_video.rename(new_video)
    except Exception:
        pass

@pytest.fixture
def page(context):
    page = context.new_page()
    # Apply standard viewport
    page.set_viewport_size({"width": 1280, "height": 720})
    yield page
    page.close()

@pytest.fixture
def authenticated_page(context):
    \"\"\"Login and navigate to welcome page with proper waits\"\"\"
    page = context.new_page()
    page.set_viewport_size({"width": 1280, "height": 720})
    
    try:
        from config.urls import LOGIN_URL, WELCOME_URL
        page.goto(LOGIN_URL, timeout=30000)
    except (ImportError, AttributeError):
        yield page
        return

    # Fill credentials if provided in environment
    email = os.getenv("LOGIN_EMAIL")
    password = os.getenv("LOGIN_PASSWORD")
    
    if email and password:
        try:
            # Smart selector targeting
            page.locator("input[type='email'], input[name*='email'], [placeholder*='Email']").first.fill(email)
            page.locator("input[type='password'], input[name*='password'], [placeholder*='Password']").first.fill(password)
            page.locator("button[type='submit'], button:has-text('Login'), button:has-text('Sign In')").first.click()
            page.wait_for_load_state('networkidle', timeout=15000)
        except:
            pass
    
    # Navigate to welcome page if specified
    from config.urls import WELCOME_URL
    if WELCOME_URL and WELCOME_URL not in page.url:
        page.goto(WELCOME_URL, timeout=30000)
        page.wait_for_load_state('networkidle', timeout=15000)
    
    yield page
    page.close()

def extract_simple_error(error_text):
    \"\"\"Extract simple error reason from complex stack trace\"\"\"
    error_str = str(error_text)
    if "element(s) not found" in error_str or "waiting for locator" in error_str:
        return "Element not found"
    elif "Target page, context or browser has been closed" in error_str:
        return "Browser closed unexpectedly"
    elif "AssertionError" in error_str:
        return "Assertion failed"
    elif "timeout" in error_str.lower():
        return "Timeout exceeded"
    else:
        return "Test error"

@pytest.fixture(autouse=True)
def log_test_info(request):
    # Extract page type from test file path
    test_file = request.node.fspath.basename
    page_type = test_file.replace("test_", "").replace(".py", "")
    test_name = request.node.name
    
    # Create artifacts directory structure
    artifacts_dir = Path("artifacts")
    log_dir = artifacts_dir / "logs" / page_type
    screenshot_dir = artifacts_dir / "screenshots" / page_type
    log_dir.mkdir(parents=True, exist_ok=True)
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    
    test_logger = logging.getLogger(test_name)
    test_logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    for handler in test_logger.handlers[:]:
        test_logger.removeHandler(handler)
    
    # Add file handler
    file_path = log_dir / f"{test_name}.log"
    file_handler = logging.FileHandler(str(file_path), mode='w', encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    test_logger.addHandler(file_handler)
    
    test_logger.info(f"Starting test: {test_name}")
    start_time = datetime.datetime.now()
    
    yield
    
    # Take failure screenshot if needed
    if hasattr(request.node, 'rep_call') and request.node.rep_call.failed:
        try:
            page_fixture = None
            if 'authenticated_page' in request.fixturenames:
                page_fixture = request.getfixturevalue('authenticated_page')
            elif 'page' in request.fixturenames:
                page_fixture = request.getfixturevalue('page')
            
            if page_fixture:
                screenshot_path = screenshot_dir / f"{test_name}.png"
                page_fixture.screenshot(path=str(screenshot_path))
                test_logger.info(f"Failure screenshot saved: {screenshot_path}")
        except:
            pass

    end_time = datetime.datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    if hasattr(request.node, 'rep_call'):
        if request.node.rep_call.passed:
            test_logger.info(f"✅ PASSED - {duration:.1f}s")
        elif request.node.rep_call.failed:
            failure_reason = extract_simple_error(request.node.rep_call.longrepr)
            test_logger.error(f"❌ FAILED - {duration:.1f}s - {failure_reason}")
            
            # Send failure to Triage Agent
            try:
                triage_payload = {
                    "run_id": os.getenv("TRIAGE_RUN_ID", "manual_run"),
                    "test_name": test_name,
                    "file_path": str(request.node.fspath),
                    "error_message": str(request.node.rep_call.longrepr.reprcrash.message),
                    "stack_trace": str(request.node.rep_call.longrepr),
                    "logs": file_path.read_text(encoding='utf-8') if file_path.exists() else "",
                    "llm_model": os.getenv("TRIAGE_LLM_MODEL", "gemma:2b"),
                    "bert_url": os.getenv("TRIAGE_BERT_URL", "http://localhost:8006/predict")
                }
                requests.post("http://localhost:8004/api/triage", json=triage_payload, timeout=60)
                test_logger.info("Sent failure report to Triage Agent")
            except Exception as e:
                test_logger.warning(f"Failed to send report to Triage Agent: {e}")
    else:
        test_logger.info(f"COMPLETED - {duration:.1f}s")

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)
"""
    write_file(OUTPUT_TESTS_DIR / "conftest.py", content.strip())
    print("conftest.py generated")

# =========================
# GENERATE TESTS PER PAGE
# =========================
def generate_page_tests(page: str, base_prompt: str):
    # Read locators and test cases
    locator_code = read_file(CONFIG_DIR / f"{page}_locators.py")
    testcase_code = read_file(TESTCASES_DIR / f"{page}_testcases.json")
    
    if not locator_code:
        print(f"Warning: No locators found for {page}")
        return
        
    if not testcase_code:
        print(f"Warning: No test cases found for {page}")
        return
    
    # Create comprehensive prompt for LLM
    page_prompt = f"""
{base_prompt}

PAGE: {page}
URL_VARIABLE: {page.upper().replace(" ", "_").replace("-", "_")}_URL
LOCATOR_CLASS: {get_locator_class(page)}

LOCATORS FILE CONTENT:
{locator_code}

TEST CASES JSON:
{testcase_code}

INSTRUCTIONS:
1. Read the locators from the {page}_locators.py file
2. Read the test cases from the JSON file
3. Generate one test function per test case using the specific inputs from each test case
4. Use the locator class references (e.g., {get_locator_class(page)}.EMAIL_INPUT)
5. Use the actual input values from each test case (not hardcoded values)
6. Use the provided URL_VARIABLE for navigation
7. For pages requiring authentication (e.g., welcome, dashboard), use authenticated_page fixture; for others use page fixture
8. Add proper assertions based on test case expectations

Generate complete Playwright pytest test file. Output ONLY Python code.
"""
    
    try:
        # Call LLM to generate tests
        print(f"Generating tests for {page} using LLM...")
        raw_output = call_llm(page_prompt)
        
        # Extract code from LLM response
        test_code = extract_code_only(raw_output)
        
        # Apply post-processing
        test_code = inject_pythonpath(test_code)
        test_code = fix_locator_usage(test_code)
        
        # Determine output file
        test_dir = OUTPUT_TESTS_DIR / page
        existing_files = list(test_dir.glob("*test*.py")) if test_dir.exists() else []
        
        if existing_files:
            out_path = existing_files[0]
        else:
            out_path = test_dir / f"test_{page}.py"
        
        write_file(out_path, test_code)
        
        print(f"Generated {out_path.name} for {page} using LLM")
        
    except Exception as e:
        print(f"Error generating tests for {page}: {e}")
        # Fallback to direct generation if LLM fails
        print(f"Falling back to direct generation for {page}")
        generate_page_tests_fallback(page)

# =========================
# MAIN
# =========================
def main():
    print("Generating tests using LLM (Groq) integration")

    base_prompt = read_file(PROMPT_FILE)
    if not base_prompt:
        raise RuntimeError("prompt.txt is empty or missing")

    pages = infer_pages()
    if not pages:
        raise RuntimeError("No pages detected")

    generate_conftest()

    for page in pages:
        generate_page_tests(page, base_prompt)

    print("LLM-based test generation completed successfully")

if __name__ == "__main__":
    main()