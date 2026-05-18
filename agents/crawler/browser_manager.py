import asyncio
import os
import sys
import logging
import random
import subprocess
from typing import Optional, Any, Dict
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

# Add parent directory to path to import config if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import CrawlerConfig

logger = logging.getLogger("qa_crawler.browser")

class BrowserSession:
    """
    Context manager for Playwright browser lifecycle.
    Ensures deterministic cleanup of playwright, browser, and context.
    """
    def __init__(self, config: CrawlerConfig):
        self.config = config
        self.playwright = None
        self.browser = None
        self.context = None
        self.current_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    async def __aenter__(self):
        try:
            self.playwright = await async_playwright().start()
            
            # 1. Launch Browser
            self.browser = await self._launch_browser()
            
            # 2. Setup Context
            self.context = await self._create_context()
            
            return self
        except Exception as e:
            logger.error(f"Failed to initialize BrowserSession: {e}")
            await self._cleanup()
            raise

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            logger.warning(f"BrowserSession exiting due to exception: {exc_val}")
        await self._cleanup()

    async def _launch_browser(self):
        """Launch appropriate browser based on config (Camoufox or Chromium)"""
        if self.config.use_camoufox:
            return await self._init_camoufox()
        
        logger.info(f"Launching Chromium (headless={self.config.headless})...")
        browser_args = [
            '--start-maximized',
            '--disable-blink-features=AutomationControlled'
        ]
        return await self.playwright.chromium.launch(
            headless=self.config.headless, 
            args=browser_args
        )

    async def _create_context(self) -> BrowserContext:
        """Create a new context with stealth and viewport settings"""
        width = self.config.viewport_width
        height = self.config.viewport_height
        
        if self.config.random_viewport:
            width += random.randint(-50, 50)
            height += random.randint(-30, 30)

        context_args = {
            "user_agent": self.current_ua,
            "permissions": ['notifications'],
            "viewport": {'width': width, 'height': height}
        }
        
        if self.config.mobile_emulation:
            context_args.update({
                "is_mobile": True,
                "has_touch": True,
                "device_scale_factor": 2
            })

        logger.info(f"Creating browser context (Viewport: {width}x{height}, Mobile: {self.config.mobile_emulation})")
        return await self.browser.new_context(**context_args)

    async def _init_camoufox(self) -> Any:
        """Initialize Camoufox with stealth presets and auto-fetch."""
        try:
            from camoufox.async_api import AsyncCamoufox
        except ImportError:
            logger.warning("Camoufox package not found. Falling back to standard Firefox.")
            return await self.playwright.firefox.launch(headless=True)

        launch_kwargs = {
            "headless": self.config.camoufox_headless_mode if self.config.camoufox_headless_mode != "true" else True,
            "os": "windows"
        }
        
        if sys.platform != "linux" and launch_kwargs["headless"] == "virtual":
            logger.warning("Virtual display is Linux-only. Falling back to standard headless=True.")
            launch_kwargs["headless"] = True
            
        logger.info(f"Initializing Camoufox (Headless: {launch_kwargs['headless']})...")

        try:
            return await AsyncCamoufox(**launch_kwargs).start()
        except Exception as e:
            if "binary" in str(e).lower() or "not found" in str(e):
                logger.warning("Camoufox binary missing. Attempting auto-fetch...")
                try:
                    subprocess.run([sys.executable, "-m", "camoufox", "fetch"], check=True, capture_output=True)
                    return await AsyncCamoufox(**launch_kwargs).start()
                except Exception as fe:
                    logger.error(f"Auto-fetch failed: {fe}")
                    return await self.playwright.firefox.launch(headless=True)
            else:
                logger.error(f"Camoufox init error: {e}")
                return await self.playwright.firefox.launch(headless=True)

    async def rotate(self):
        """Safely recreate the browser context to clear memory and cookies."""
        logger.info("Rotating browser context...")
        if self.context:
            await self.context.close()
        
        # If using Camoufox and we want a totally fresh browser, we might need to restart the browser too
        # but usually context rotation is enough for memory/cookies.
        # If Chromium, just a new context is fine.
        self.context = await self._create_context()
        logger.info("Rotation complete.")

    async def _cleanup(self):
        """Standardized cleanup for high-stability SDET operations"""
        try:
            if self.context:
                await self.context.close()
                self.context = None
            if self.browser:
                await self.browser.close()
                self.browser = None
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
            logger.info("BrowserSession cleanup complete.")
        except Exception as e:
            logger.error(f"Error during BrowserSession cleanup: {e}")

    async def new_page(self) -> Page:
        """Helper to create a page within the managed context"""
        if not self.context:
            raise RuntimeError("BrowserSession context is not initialized. Use 'async with' block.")
        page = await self.context.new_page()
        
        # Default security/anti-tracking routes
        await self.context.route("**/*", lambda route: 
            route.abort() if any(p in route.request.url.lower() for p in ['analytics', 'hotjar', 'gtm', 'facebook', 'pixel', 'doubleclick']) 
            else route.continue_()
        )
        
        page.on("dialog", lambda dialog: asyncio.create_task(dialog.dismiss()))
        return page
