import os
import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

# Configure modular logging
logger = logging.getLogger("qa_crawler.rich_interactions")

try:
    from browser_use import Agent, Browser, BrowserProfile
    HAS_RICH_DEPS = True
except ImportError:
    HAS_RICH_DEPS = False
    logger.warning("Optional AI dependencies (browser-use) not found. Rich interactions will be disabled.")

try:
    from langchain_groq import ChatGroq
    from langchain_openai import ChatOpenAI
    from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
    from langchain_google_genai import ChatGoogleGenerativeAI
    HAS_LANGCHAIN_DEPS = True
except ImportError:
    HAS_LANGCHAIN_DEPS = False
    logger.warning("Optional AI dependencies (langchain-groq, langchain-google-genai, etc.) not found. Rich interactions will be disabled.")

try:
    from tenacity import retry, stop_after_attempt, wait_exponential
except ImportError:
    # Fallback if tenacity missing
    def retry(*args, **kwargs):
        return lambda f: f
    def stop_after_attempt(*args): return None
    def wait_exponential(*args, **kwargs): return None


from pydantic import SecretStr, Field, ConfigDict

class BrowserCompatibleGroq(ChatGroq):
    model_config = ConfigDict(extra="allow")
    provider: str = "groq"
    @property
    def model(self): return getattr(self, "model_name", "unknown")

class BrowserCompatibleOpenAI(ChatOpenAI):
    model_config = ConfigDict(extra="allow")
    provider: str = "openai"
    @property
    def model(self): return getattr(self, "model_name", "unknown")

class BrowserCompatibleHuggingFace(ChatHuggingFace):
    model_config = ConfigDict(extra="allow")
    provider: str = "huggingface"
    @property
    def model(self): return getattr(self, "model_id", "unknown")

class BrowserCompatibleGemini(ChatGoogleGenerativeAI):
    model_config = ConfigDict(extra="allow")
    provider: str = "google"
    @property
    def model(self): return getattr(self, "model", "unknown")

class RichInteractionManager:
    """
    Leverages a multi-provider LLM chain (Groq -> OpenRouter -> Hugging Face)
    to perform autonomous exploration and interaction on complex web pages.
    """
    def __init__(self, api_key: str = None):
        if not HAS_RICH_DEPS or not HAS_LANGCHAIN_DEPS:
            logger.warning("Rich Interaction Manager: Core dependencies missing. Class will be disabled.")
            self.llm = None
            return

        self.screen_id_counter = 0
        self.llm = self._init_llm(api_key)
        
        if not self.llm:
            logger.error("Rich Interaction Manager: No LLM provider available after fallback attempts.")

    def _init_llm(self, override_key: str = None):
        """
        Initializes LLM with a priority fallback chain:
        1. Gemini (Primary per user request)
        2. Groq (Fastest)
        3. OpenRouter (Reliable)
        4. Hugging Face (Backup)
        """
        gemini_key = os.getenv("GEMINI_API_KEY")
        groq_key = override_key or os.getenv("GROQ_API_KEY")
        or_key = os.getenv("OPENROUTER_API_KEY")
        hf_key = os.getenv("HUGGINGFACEHUB_API_TOKEN")

        # 1. Primary: Gemini
        try:
            if gemini_key:
                logger.info("Using Gemini (Primary - Gemini 2.0 Flash)")
                return BrowserCompatibleGemini(
                    model="gemini-2.0-flash",
                    api_key=SecretStr(gemini_key),
                    temperature=0.1,
                    max_output_tokens=2048
                )
        except Exception as e:
            logger.warning(f"Gemini initialization failed: {e}")

        # 2. Secondary: Groq
        try:
            if groq_key:
                logger.info("Using Groq (Primary - Llama 3.3 70B)")
                return BrowserCompatibleGroq(
                    model="llama-3.3-70b-versatile",
                    api_key=SecretStr(groq_key),
                    temperature=0.1,
                    max_tokens=2048
                )
        except Exception as e:
            logger.warning(f"Groq initialization failed: {e}")

        # 2. Fallback: OpenRouter
        try:
            if or_key:
                logger.info("Falling back to OpenRouter (Llama 3.1 70B)")
                return BrowserCompatibleOpenAI(
                    model="meta-llama/llama-3.1-70b-instruct",
                    api_key=SecretStr(or_key),
                    base_url="https://openrouter.ai/api/v1",
                    temperature=0.1,
                    max_tokens=2048
                )
        except Exception as e:
            logger.warning(f"OpenRouter initialization failed: {e}")

        # 3. Fallback: Hugging Face
        try:
            if hf_key:
                logger.info("Falling back to Hugging Face (Llama 3.1 8B)")
                return BrowserCompatibleHuggingFace(
                    llm=HuggingFaceEndpoint(
                        repo_id="meta-llama/Meta-Llama-3.1-8B-Instruct",
                        huggingfacehub_api_token=hf_key,
                        temperature=0.1,
                        max_new_tokens=2048,
                        timeout=60
                    )
                )
        except Exception as e:
            logger.warning(f"Hugging Face initialization failed: {e}")

        return None

    async def explore_and_interact(self, url: str, prompt: str = None, page: Optional[Any] = None, timeout_sec: int = 60):
        """
        Launches an autonomous agent to explore the page based on a goal.
        Includes retry logic for transient LLM failures.
        """
        if not self.llm:
            return "AI Key or dependencies missing. Skipping rich interaction."

        # v6.0 World-Class SDET Persona (Exhaustive Mode)
        goal = prompt or (
            f"You are a World-Class SDET and Award-Winning Automation Engineer with a reputation for thinking 'out of the box' to achieve 100% coverage.\n"
            f"Current URL: {url}\n\n"
            "Mission: Perform an exhaustive 'Absolute Interaction' crawl. Your goal is NOT just a basic scan, but to EXERCISE EVERY INTERACTIVE STATE.\n\n"
            "Exhaustive Testing Instructions:\n"
            "1. FORMS: Locate and fill EVERY field. Do not use placeholders if real data is logical. Type realistic values. Use login credentials if provided in the GOAL context.\n"
            "2. DROPDOWNS: Click every dropdown you find. For each dropdown, you MUST extract all available options. Select one option to trigger potential dynamic content.\n"
            "3. BUTTONS/TOGGLES: Click every button. If a button looks like a toggle (On/Off), click it multiple times to observe state changes.\n"
            "4. MODALS/REVEALS: Specifically hunt for elements that reveal hidden sections. If a click opens a modal or a menu, explore the content inside immediately.\n"
            "5. NAVIGATION: Identify buttons that lead to new pages. Use them to map the full application flow.\n"
            "6. REPORT EVERYTHING: Your output must reflect all revealed options, state changes, and newly discovered elements.\n\n"
            "REPORT IN STRUCTURED JSON ONLY:\n"
            "{\n"
            "  \"page_url\": \"" + url + "\",\n"
            "  \"area_tested\": \"Exhaustive Component Exercise\",\n"
            "  \"interactions\": [\n"
            "    {\"element\": \"Dropdown: Plan Select\", \"action\": \"Opened and extracted 3 options: Basic, Pro, Enterprise\", \"result\": \"Pro selected\"},\n"
            "    {\"element\": \"Toggle: Dark Mode\", \"action\": \"Clicked twice\", \"result\": \"Verified On/Off state change\"}\n"
            "  ],\n"
            "  \"observed_result\": \"Discovered 5 new elements inside the revealed pricing modal\",\n"
            "  \"human_readable_locators\": \"Enabled\",\n"
            "  \"confidence\": 100\n"
            "}\n"
            "IMPORTANT: If authentication credentials (email/password) are provided, you MUST use them EXACTLY. If the page is at a success state, report it and look for the next deep interaction."
        )
        
        return await self._execute_agent_run(url, goal, page, timeout_sec)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _execute_agent_run(self, url: str, goal: str, page: Optional[Any] = None, timeout_sec: int = 60):
        """Encapsulated execution with retry logic"""
        if not page:
             raise ValueError("RichInteractionManager requires an existing page for session sharing to prevent context loss.")

        try:
            logger.info(f"Using existing shared context for AI interaction on {url}")
            try:
                agent = Agent(
                    task=goal,
                    llm=self.llm,
                    browser_context=page.context
                )
                logger.info(f"Starting SDET Agent on shared page: {url}...")
                history = await agent.run(max_steps=10)
            except AssertionError as e:
                if "CDP client not initialized" in str(e):
                    logger.warning("CDP Error detected. browser-use requires a CDP-compatible browser (Chromium). Falling back to basic scan.")
                    return await self._basic_page_scan(page)
                raise e
            
            # Extract result
            result = None
            if history and hasattr(history, 'final_result'):
                result = history.final_result()
            
            if not result:
                logger.warning("Agent returned None or empty result -> using basic scan fallback")
                return await self._basic_page_scan(page)

            logger.info(f"SDET Agent Run Complete (Shared Context). Result: {result[:100]}...")
            return result

        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            raise # Let retry handle it

    async def fill_form(self, url: str, form_description: str, page: Optional[Any] = None):
        """Legacy helper updated for shared context"""
        return await self.explore_and_interact(url, f"Fill form: {form_description}", page)

    async def _basic_page_scan(self, page):
        """Fallback for when LLM agent fails to produce a result"""
        try:
            elements = await page.query_selector_all("input:not([type='hidden']), button, select, textarea, a.btn, a.nav-link")
            return f"Basic scan: {len(elements)} interactive elements found. AI interaction failed but page parsed."
        except Exception as e:
            return f"Basic scan failed: {e}"
