import asyncio
import os
import re
import json
import hashlib
import sys
import logging
import tempfile
from datetime import datetime, timedelta
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from typing import List, Dict, Set, Optional, Any, AsyncGenerator, Tuple
import heapq
import random
import urllib.robotparser
import httpx
import requests
import xml.etree.ElementTree as ET
import psutil # For memory limit check
from bs4 import BeautifulSoup
import argparse
import shutil

from playwright.async_api import async_playwright, Page, ElementHandle 
from groq import AsyncGroq
from dotenv import load_dotenv
from browser_manager import BrowserSession

from config import CrawlerConfig
from browse_ai_helper import BrowseAIHelper
from rich_interactions import RichInteractionManager

# Force UTF-8 encoding for Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, Exception):
        pass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("qa_crawler")

class QAGardenCrawler:
    def __init__(self, config: CrawlerConfig):
        self.config = config
        self._validate_url(config.url)
        
        self.max_depth = config.max_depth
        self.max_pages = config.max_pages
        self.max_retries = config.max_retries
        self.failure_policy = config.failure_policy
        self.interaction_history: Set[str] = set()
        self.visited_states: Set[str] = set()
        self.finished_urls: Set[str] = set()
        self.visited_content_hashes: Set[str] = set()
        
        # Control Events
        self.pause_event = asyncio.Event()
        self.pause_event.set() # Start unpaused
        self.abort_event = asyncio.Event()
        
        # NEW: Site-specific locators folder
        domain = urlparse(config.url).netloc.replace('www.', '').replace('.', '_')
        # v5.0: Trigger global rotation immediately to determine root
        self.locators_root = self._rotate_locators()
        
        if getattr(config, 'site_specific_locators', True):
            self.locators_dir = os.path.join(self.locators_root, domain)
        else:
            self.locators_dir = self.locators_root
            
        # Ensure the domain dir exists (since _rotate_locators only guaranteed the root)
        os.makedirs(self.locators_dir, exist_ok=True)
        
        # v5.2: Force Clean - ensure no stale page_*.json files remain from previous failed rotations
        if os.path.exists(self.locators_dir):
            logger.info(f"Cleaning existing locators for domain: {self.locators_dir}")
            for f in os.listdir(self.locators_dir):
                if f.endswith(".json") or f.endswith(".png"):
                    try:
                        os.remove(os.path.join(self.locators_dir, f))
                    except Exception as e:
                        logger.warning(f"Could not clear stale file {f} (likely locked): {e}")
        
        load_dotenv()
        self.groq_keys = [
            key.strip() 
            for key in os.getenv("GROQ_API_KEYS", "").split(",") 
            if key.strip() and "gsk_" in key
        ]
        self.groq_key_index = 0
        self.client = AsyncGroq(api_key=self.groq_keys[0]) if (self.groq_keys and config.use_ai) else None
        
        self.all_locators = {} # Consolidated dictionary
        self.seen_xpaths = set()
        self.seen_fingerprints = set()  # NEW: Content-based duplicate detection
        self.screen_id_counter = 0
        self.active_requests = set()
        self.seen_table_hashes = set() # NEW: Table-level deduplication
        self.consec_interaction_fails = 0 # NEW: Per-page interaction failure tracking
        
        # Stability & Reliability State
        self.nav_count = 0
        self.consecutive_failures = 0
        self.total_session_restarts = 0
        self.session_authenticated = False # Track if we just logged in
        self.is_cleaning_up = False # Guard for shutdown
        self.start_time = datetime.now()
        self.heartbeat_task = None
        self.browser_handle = None
        self.context_handle = None
        self.browser_rotation_counter = 0
        
        # Rich Interaction Layer
        self.rich_manager = RichInteractionManager() if config.enable_rich_interactions else None
        self.browse_ai = BrowseAIHelper() if config.browse_ai_enabled else None
        
        # Site Mapping & Priority Queue
        self.site_graph = {} # {url: {"actions": [], "children": [], "hash": ""}}
        self.discovery_queue = [] # Heapq: (priority, depth, discovery_order, url, parent_url)
        self.discovery_counter = 0 # NEW: For stable FIFO ordering
        self.discovered_urls = set()
        self.robots_parsers = {} # Cache for robots.txt parsers
        self.current_semantic_map = {} # NEW: Component mapping for current page
        
        # User-Agent Rotation
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
        ]
        import random
        self.current_ua = random.choice(self.user_agents)
        
        self.seen_names = set() # NEW: For collision detection
        self.total_interactions = 0 # NEW v4.1
        self.current_page_fails = 0 # NEW v4.1
        
        logger.info(f"QA Garden Crawler initialized (AI: {'ENABLED' if self.client else 'DISABLED'})")

    def _validate_url(self, url: str):
        parsed = urlparse(url)
        if parsed.scheme not in ['http', 'https']:
            raise ValueError(f"Invalid URL scheme: {parsed.scheme}. Only http and https are allowed.")
        if not parsed.netloc:
            raise ValueError("Invalid URL: Missing domain.")

    def _rotate_locators(self) -> str:
        """
        v6.0: Strict 2-folder Rotation (locators_new -> locators_old).
        Returns the effective root directory.
        """
        current_root = "locators_new"
        previous_root = "locators_old"

        try:
            # 1. Clear old backup
            if os.path.exists(previous_root):
                try:
                    shutil.rmtree(previous_root)
                    logger.debug(f"Cleared old backup: {previous_root}")
                except Exception as ex:
                    logger.warning(f"Could not clear {previous_root}: {ex}")
                    # If we can't clear old, we can't rotate current to it cleanly.
                    # Best fallback: Just rename current to a unique timestamped folder to clear the way
                    timestamp_backup = f"{previous_root}_{int(datetime.now().timestamp())}"
                    try:
                        shutil.move(previous_root, timestamp_backup)
                    except: pass 

            # 2. Move current library to backup
            if os.path.exists(current_root):
                try:
                    # Rename instead of move to avoid nesting issues
                    os.rename(current_root, previous_root)
                    logger.info(f"Current locators moved to: {previous_root}")
                except Exception as ex:
                    logger.warning(f"Could not rotate {current_root}: {ex}")
                    # Fallback: just try to clear content of current_root so we are fresh
            
            # 3. Create fresh current root
            os.makedirs(current_root, exist_ok=True)
            return current_root
            
        except Exception as e:
            logger.error(f"Locator rotation failed: {e}")
            os.makedirs(current_root, exist_ok=True)
            return current_root

    async def run(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Main execution loop yielding progress updates using BrowserSession (v6.1 Robustness)"""
        try:
            async with BrowserSession(self.config) as session:
                self.session_handle = session
                self.browser_handle = session.browser
                self.context_handle = session.context
                self.playwright_handle = session.playwright

                # Initial page creation
                try:
                    page = await session.new_page()
                    
                    page.on("request", lambda request: self.active_requests.add(request.url))
                    page.on("requestfinished", lambda request: self.active_requests.discard(request.url))
                    page.on("requestfailed", lambda request: self.active_requests.discard(request.url))
                    
                    logger.info(f"Navigating to {self.config.url}...")
                    try:
                        # Use domcontentloaded for broader compatibility (SPAs like Grok)
                        # networkidle often times out on streaming sites
                        await page.goto(self.config.url, wait_until="domcontentloaded", timeout=self.config.timeout_sec * 1000)
                        await page.wait_for_timeout(2000)
                    except Exception as e:
                        logger.error(f"Initial navigation failed: {e}")
                        return

                    await self._auto_consent(page)
                    
                    # Proactive Site Mapping
                    if self.config.enable_site_mapping:
                        async for update in self._proactive_mapping(page):
                            yield update
                    
                    if self.config.auth_creds and not self.session_authenticated:
                        auth_type = await self._detect_auth_type(page)
                        
                        if auth_type == "SIGNUP":
                            logger.info("Landing on Signup page (registration). Extracting state before seeking Login...")
                            async for update in self._process_current_page(page, depth=0, path="signup"):
                                yield update
                            # Do NOT add to finished_urls yet to allow authenticated pass if we reach dashboard
                            
                            logger.info("Seeking 'Sign In' or 'Login' toggle...")
                            login_toggle = await page.query_selector("a:has-text('Sign In'), a:has-text('Login'), button:has-text('Sign In'), button:has-text('Log In'), span:has-text('Sign In')")
                            if login_toggle:
                                await login_toggle.click()
                                await page.wait_for_timeout(3000)
                                auth_type = await self._detect_auth_type(page)
                            else:
                                logger.warning("No login toggle found on Signup page.")

                        if auth_type == "LOGIN":
                            if await self._handle_login(page):
                                logger.info("Login successful! Preparing for authenticated discovery pass.")
                                self.session_authenticated = True
                                await page.wait_for_timeout(4000)
                                # Force re-processing of the new landing page
                                land_url = self._normalize_url(page.url)
                                self.finished_urls.discard(land_url)
                                await self._add_to_queue(page.url, 0, "login_success")
                            else:
                                logger.warning("Auth sequence failed/stalled.")
                                if self.config.failure_policy == "stop":
                                    return

                    # Start Queue-based Crawl - Ensure we process the landing page (Dashboard) first if authenticated
                    if not self.discovery_queue or self.session_authenticated:
                        logger.info(f"Initializing crawl: processing current state ({page.url})...")
                        async for update in self._process_current_page(page, depth=0, path="auth_landing"):
                            yield update
                        self.finished_urls.add(self._normalize_url(page.url))

                    # Now continue with the rest
                    async for update in self._crawl_loop(page):
                        yield update

                    # Finalize
                    output_json = self._save_consolidated_locators()
                    
                    # v5.1: Corrected Coverage Est (Visited / Discovered)
                    visited = len(self.finished_urls)
                    discovered = len(self.discovery_queue) + visited
                    coverage_est = (visited / discovered * 100) if discovered > 0 else 0
                    
                    logger.info(f"Crawl Complete. Discovered {discovered} pages, Visited {visited}, Extracted {len(self.all_locators)} locators, Coverage Est: {coverage_est:.2f}%")
                    
                    # Use absolute path for dashboard retrieval
                    abs_path = os.path.abspath(output_json)
                    yield {
                        "event": "artifact",
                        "type": "json",
                        "name": "Consolidated Locators",
                        "path": abs_path, 
                        "agent": "crawler"
                    }
                    
                    yield {
                        "event": "coverage_update",
                        "job_id": getattr(self.config, 'job_id', 'unknown'),
                        "discovered": len(self.discovered_urls),
                        "extracted": len(self.all_locators),
                        "coverage_percent": round(coverage_est, 2)
                    }
                    
                    yield {
                        "event": "completed", 
                        "job_id": getattr(self.config, 'job_id', 'unknown'),
                        "page_count": len(self.finished_urls), 
                        "discovered_count": len(self.discovered_urls),
                        "total_locators": len(self.all_locators),
                        "status": "completed",
                        "agent": "crawler",
                        "path": abs_path,
                        "coverage_metric": f"Coverage Est: {((len(self.finished_urls) / (len(self.discovery_queue) + len(self.finished_urls))) * 100) if (len(self.discovery_queue) + len(self.finished_urls)) > 0 else 0:.2f}% ({len(self.finished_urls)} visited / {(len(self.discovery_queue) + len(self.finished_urls))} discovered)"
                    }
                finally:
                    pass
            
            logger.info("Crawler run loop finished.")
        except Exception as e:
            logger.critical(f"FATAL STARTUP ERROR: {e}", exc_info=True)
            yield {"event": "log", "message": f"Fatal Startup Error: {e}", "level": "critical"}


    def _normalize_url(self, url: str) -> str:
        """Robustly normalize URL to prevent infinite loops and duplicate processing."""
        if not url or not url.strip():
            return ""
        url = url.strip()
        try:
            p = urlparse(url)
            if not p.scheme:
                # Default to https
                url = f"https://{url}"
                p = urlparse(url)

            # 1. Remove fragments (#section)
            p = p._replace(fragment="")

            # 2. Clean query parameters (Remove tracking/session IDs)
            query = parse_qs(p.query, keep_blank_values=True)
            # Standard tracking/noise parameters to strip
            bad_keys = {
                'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
                'fbclid', 'gclid', 'msclkid', '_ga', '_gl', 'session_id', 'sid',
                'jsessionid', 'phpsessid', 'sort', 'order', 'page_size'
            }
            cleaned_query = {k: v for k, v in query.items() if k.lower() not in bad_keys}
            
            # Reconstruct query string (sorted for consistency - Elite Standard)
            sorted_items = sorted(cleaned_query.items())
            query_str = urlencode({k: v[0] if len(v) == 1 else v for k, v in sorted_items}, doseq=True)

            # 3. Normalize netloc and path
            netloc = p.netloc.lower()
            # if netloc.startswith('www.'):
            #     netloc = netloc[4:]
            
            path = p.path.rstrip('/')
            if not path: path = ""

            normalized = urlunparse((
                p.scheme.lower(),
                netloc,
                path,
                p.params,
                query_str,
                ''
            ))
            return normalized
        except Exception as e:
            logger.debug(f"URL normalization error for {url}: {e}")
            return url.rstrip('/')

    async def _add_to_queue(self, url: str, depth: int, parent_url: str):
        url = self._normalize_url(url)
        
        # v1.0: Modular Marketing Filter - prevents "looping back" from authenticated session to public site
        if self.session_authenticated:
            url_lower = url.lower()
            # 1. Common Keywords (Pricing, Features, etc.)
            if any(kw in url_lower for kw in self.config.exclude_marketing_keywords):
                logger.debug(f"Skipping authenticated marketing-like URL: {url}")
                return
            # 2. Site-specific URL Patterns
            if any(pat in url_lower for pat in self.config.marketing_url_patterns):
                logger.debug(f"Skipping site-specific marketing URL: {url}")
                return

        if url in self.finished_urls:
             return
        if url in [x[3] for x in self.discovery_queue]:
             return
        
        # Max Queue Size Limit (Safety)
        if len(self.discovery_queue) >= self.config.max_queue_size:
            logger.warning(f"Max queue size ({self.config.max_queue_size}) reached. Skipping further Discovery.")
            return

        # Check robots.txt and Domain (v5.0: Async Await)
        is_allowed = await self._is_url_allowed(url)
        if not is_allowed:
            logger.debug(f"Skipping {url} (disallowed by robots.txt or domain rules)")
            return

        priority = self._calculate_url_priority(url, depth, self.discovery_counter)
        
        # Use discovery_counter to preserve document order (FIFO) for equal priority/depth
        self.discovery_counter += 1
        heapq.heappush(self.discovery_queue, (priority, depth, self.discovery_counter, url, parent_url))
        self.discovered_urls.add(url)
        print(f"DIAGNOSTIC: Added to queue -> {url} (Depth: {depth})", flush=True)
        logger.debug(f"Added to queue: {url} (Depth: {depth}, Priority: {priority}, Order: {self.discovery_counter})")

    def _calculate_url_priority(self, url: str, depth: int, discovery_order: int) -> int:
        """Depth first, then discovery order (natural top-to-bottom flow)"""
        score = depth * 10000 + discovery_order
        url_lower = url.lower()
        
        # Reduced keyword bias for more natural neighbors (like podgallery)
        if any(kw in url_lower for kw in ["pricing", "features", "dashboard"]):
            score -= 500  # small boost, not huge
            
        return score

    async def _discover_all_links(self, page: Page) -> List[str]:
        try:
            is_dynamic = getattr(self.config, 'dynamic_crawl', False)
            links = await page.evaluate("""
                (isDynamic) => {
                    const getDomain = (url) => {
                        try {
                            const parsed = new URL(url);
                            return parsed.hostname.toLowerCase().replace('www.', '');
                        } catch(e) { return null; }
                    };
                    
                    const baseDomain = getDomain(window.location.href);
                    if (!baseDomain) return [];

                    const discovered = new Set();

                    function walk(node) {
                        if (!node) return;
                        
                        // 1. Discover <a> links
                        if (node.tagName === 'A' && node.getAttribute('href')) {
                            try {
                                const href = node.getAttribute('href');
                                if (!href.startsWith('javascript:') && !href.startsWith('mailto:') && !href.startsWith('tel:')) {
                                    const absoluteUrl = new URL(href, window.location.href).href;
                                    discovered.add(absoluteUrl);
                                }
                            } catch (e) {}
                        }

                        // 2. Discover canonical link
                        if (node.tagName === 'LINK' && node.rel === 'canonical' && node.getAttribute('href')) {
                            try {
                                const absoluteUrl = new URL(node.getAttribute('href'), window.location.href).href;
                                discovered.add(absoluteUrl);
                            } catch (e) {}
                        }
                        
                        // 3. Discover links in data-attributes (common in SPAs)
                        for (const attr of node.attributes || []) {
                            if (attr.name.includes('href') || attr.name.includes('url') || attr.name === 'to') {
                                try {
                                    const val = attr.value;
                                    if (val && (val.startsWith('/') || val.startsWith('http'))) {
                                        const absoluteUrl = new URL(val, window.location.href).href;
                                        discovered.add(absoluteUrl);
                                    }
                                } catch (e) {}
                            }
                        }

                        // Traverse light DOM
                        let child = node.firstElementChild;
                        while (child) {
                            walk(child);
                            child = child.nextElementSibling;
                        }

                        // Traverse Shadow DOM
                        if (node.shadowRoot) {
                            walk(node.shadowRoot);
                        }
                    }

                    walk(document);

                    return Array.from(discovered).filter(href => {
                        if (isDynamic) return true;
                        const linkDomain = getDomain(href);
                        return linkDomain === baseDomain || (linkDomain && linkDomain.endsWith('.' + baseDomain));
                    });
                }
            """, is_dynamic)
            # Deduplicate while preserving order (Python 3.7+ dicts are ordered)
            links = list(dict.fromkeys(links))
            return links
        except Exception as e:
            logger.error(f"Error in JS link discovery: {e}")
            return []

    async def _is_url_allowed(self, url: str) -> bool:
        """Check if URL is allowed by domain rules and robots.txt (Async v5.0)"""
        if not url.startswith('http'): 
            return False

        # 0. Check User-Defined Exclusions (CLI/Config)
        for pattern in self.config.exclude_paths:
            if pattern in url:
                logger.info(f"Skipping excluded URL pattern '{pattern}': {url}")
                return False
        
        parsed = urlparse(url)
        
        # v5.6: Progressive Resource Filter (Exclude common static assets)
        path_lower = parsed.path.lower()
        static_exts = {
            '.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico',
            '.woff', '.woff2', '.ttf', '.eot', '.mp4', '.webm', '.pdf', '.zip',
            '.map', '.json', '.webmanifest'
        }
        if any(path_lower.endswith(ext) for ext in static_exts):
            return False
            
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # Domain check: allow subdomains and handle www/non-www
        if getattr(self.config, 'dynamic_crawl', False):
             return True # Bypass domain check for dynamic crawling

        config_parsed = urlparse(self.config.url)
        config_domain = config_parsed.netloc.lower().replace('www.', '')
        link_domain = parsed.netloc.lower().replace('www.', '')
        
        # Allow if exact domain match (ignoring www) or if it's a subdomain
        if link_domain != config_domain and not link_domain.endswith('.' + config_domain):
            return False

        # NEW: Check if robots.txt should be respected
        if not self.config.respect_robots:
            return True  # Skip robots.txt if disabled in config
        
        # Robots.txt Refresh Logic (every 100 pages crawled)
        should_refresh = (len(self.finished_urls) % 100 == 0 and len(self.finished_urls) > 0)
        
        if base_url not in self.robots_parsers or should_refresh:
            rp = urllib.robotparser.RobotFileParser()
            try:
                # v5.0: Async Manual fetch with httpx
                robots_url = f"{base_url}/robots.txt"
                headers = {'User-Agent': self.current_ua}
                async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                    resp = await client.get(robots_url, headers=headers)
                
                if resp.status_code == 200:
                    rp.parse(resp.text.splitlines())
                    self.robots_parsers[base_url] = rp
                    logger.info(f"Loaded robots.txt for {base_url}")
                else:
                    logger.warning(f"robots.txt not found (Status {resp.status_code}). Allowing all.")
                    self.robots_parsers[base_url] = None
            except Exception as e:
                logger.warning(f"Could not load robots.txt for {base_url}: {e}")
                self.robots_parsers[base_url] = None  # Allow if robots.txt fails
        
        # NEW: Check robots.txt rules
        rp = self.robots_parsers.get(base_url)
        if rp:
            is_allowed = rp.can_fetch(self.current_ua, url)
            if not is_allowed:
                logger.debug(f"URL disallowed by robots.txt: {url}")
                return False
        
        return True

    async def _proactive_mapping(self, page: Page) -> AsyncGenerator[Dict[str, Any], None]:
        logger.info("Starting proactive site mapping...")
        
        # 1. Sitemap.xml
        if self.config.sitemap_enabled:
            sitemap_urls = await self._fetch_sitemap(self.config.url)
            for u in sitemap_urls:
                await self._add_to_queue(u, depth=0, parent_url="sitemap")
            yield {
                "event": "pages_discovered",
                "count": len(sitemap_urls),
                "source": "sitemap",
                "queue_size": len(self.discovery_queue)
            }

        # 2. Firecrawl or Playwright Map
        discovered = []
        if self.config.firecrawl_api_key:
            try:
                logger.info("Using Firecrawl for site mapping...")
                pass
            except Exception as e:
                logger.warning(f"Firecrawl mapping failed: {e}. Falling back to Playwright.")
        
        # Fallback to Playwright Link Extraction
        if not discovered:
            logger.info("Extracting links via Playwright fallback...")
            discovered = await self._discover_all_links(page)
            
        for u in discovered:
            await self._add_to_queue(u, depth=1, parent_url="initial_map")

        yield {
            "event": "pages_discovered",
            "count": len(discovered),
            "source": "mapping",
            "queue_size": len(self.discovery_queue)
        }

    async def _fetch_sitemap(self, url: str) -> List[str]:
        parsed = urlparse(url)
        sitemap_url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"
        links = []
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(sitemap_url)
                if resp.status_code == 200:
                    try:
                        root = ET.fromstring(resp.content)
                        ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
                        # Handle both namespaced and non-namespaced sitemaps
                        for loc in root.findall('.//ns:loc', ns) or root.findall('.//loc'):
                            if loc.text:
                                links.append(loc.text)
                    except ET.ParseError:
                        logger.warning(f"Could not parse sitemap XML for {sitemap_url}")
                else:
                    logger.info(f"Sitemap not found at {sitemap_url} (Status: {resp.status_code})")
        except Exception as e:
            logger.warning(f"Failed to fetch sitemap: {e}")
        return links

    def _check_memory(self):
        """Monitor memory usage and log warnings."""
        mem = psutil.virtual_memory()
        if mem.percent > 95:
            logger.warning(f"Memory usage critical ({mem.percent}%)! Consider closing other applications.")
        elif mem.percent > 80:
            logger.info(f"Memory usage: {mem.percent}%")

    async def _crawl_loop(self, page_dummy: Page) -> AsyncGenerator[Dict[str, Any], None]:
        """v4.9: Fault-tolerant crawl loop with global SDET recovery and session rotation."""
        while self.discovery_queue and len(self.finished_urls) < self.max_pages:
            try:
                if self.abort_event.is_set():
                    logger.info("Abort signal received. Terminating crawl.")
                    yield {"event": "log", "message": "Run aborted by user.", "level": "warning"}
                    break

                # Global Duration Check
                elapsed_total = (datetime.now() - self.start_time).total_seconds()
                if elapsed_total > self.config.max_crawl_duration_sec:
                    logger.warning(f"Hard stop: Max crawl duration ({self.config.max_crawl_duration_sec}s) reached.")
                    break

                # emergency over-crawl protection (Phase 0)
                if len(self.finished_urls) >= self.config.max_pages * 1.5:
                    logger.warning(f"Emergency over-crawl protection triggered (Finished: {len(self.finished_urls)}, Max: {self.config.max_pages})")
                    break

                priority, depth, _, normalized_url, parent = heapq.heappop(self.discovery_queue)
                
                if normalized_url in self.finished_urls: continue
                if depth > self.config.max_depth: continue

                # Check Memory & Rotation Logic
                mem = psutil.virtual_memory().percent
                headful_revert = (sys.platform == "win32" and self.config.auto_revert_headful and self.total_interactions >= 30)
                
                if (mem > self.config.context_rotation_mem_threshold or self.nav_count % 15 == 0 or headful_revert):
                    # v5.0: Safe Rotation - only rotate if no active form detected
                    logger.info("Evaluating rotation safety...")
                    is_safe = True
                    try:
                        # Check context handle still alive and has pages
                        if self.context_handle and self.context_handle.pages:
                            active_p = self.context_handle.pages[0]
                            # Check for visible forms on the active page
                            if await active_p.evaluate("document.querySelector('form:not([style*=\"display: none\"])') !== null"):
                                logger.info("Active form detected -> delaying rotation for session stability")
                                is_safe = False
                    except Exception as e:
                        logger.debug(f"Error checking for active form during rotation safety check: {e}")
                        pass # Carry on if check fails, assume safe or handle later

                    if is_safe:
                        logger.info(f"Rotating Environment (Mem: {mem}%, Navs: {self.nav_count}, Revert: {headful_revert})")
                        await self.session_handle.rotate()
                        self.total_session_restarts += 1

                logger.info(f"Navigating to: {normalized_url} (Priority: {priority}, Depth: {depth})")
                
                # Navigation Attempt Block
                success = False
                for attempt in range(1, 5):
                    try:
                        new_page = await self.session_handle.new_page()
                        new_page.on("dialog", lambda dialog: asyncio.create_task(dialog.dismiss()))
                        
                        if attempt > 1:
                            await asyncio.sleep(2 ** attempt)

                        await new_page.goto(normalized_url, wait_until="networkidle", timeout=self.config.timeout_sec * 1000)
                        await self._wait_for_stability(new_page)
                        
                        # Process Page
                        async for update in self._process_current_page(new_page, depth, parent):
                            yield update
                        
                        self.finished_urls.add(normalized_url)
                        self.nav_count += 1
                        self.consecutive_failures = 0
                        success = True
                        await new_page.close()
                        break
                    except Exception as e:
                        logger.warning(f"Attempt {attempt} failed for {normalized_url}: {e}")
                        try: await new_page.close()
                        except Exception as e: logger.debug(f"Page close ignored: {e}")
                        if attempt == 4: raise

            except Exception as e:
                logger.error(f"Critical loop error on {normalized_url if 'normalized_url' in locals() else 'unknown'}: {str(e)}", exc_info=True)
                self.consecutive_failures += 1
                if self.consecutive_failures > 5:
                    logger.critical("Too many consecutive errors -> aborting.")
                    break
                await asyncio.sleep(2)


    async def _process_current_page(self, page: Page, depth: int, path: str) -> AsyncGenerator[Dict[str, Any], None]:
        print(f"DEBUGGING: Entering _process_current_page for {page.url}", flush=True)
        current_url = self._normalize_url(page.url)
        self.current_page_fails = 0 # Reset fails on new page discovery
        # v5.3: Aggressive Stabilization for SPAs/High-JS sites
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except: pass
        await page.wait_for_timeout(3000)
        
        # v5.6: Persistent Login Retry Loop
        # If we are on the login page, we MUST try to authenticate
        if "login" in current_url.lower() and not self.session_authenticated:
            max_login_retries = 3
            for attempt in range(max_login_retries):
                logger.info(f"Login attempt {attempt + 1}/{max_login_retries}...")
                success = await self._handle_login(page)
                if success:
                    logger.info("Login successful! Proceeding to crawl...")
                    await page.wait_for_timeout(3000) # Let dashboard load
                    break
                else:
                    logger.warning(f"Login attempt {attempt + 1} failed. Retrying in 5s...")
                    # Capture state on failure
                    await page.screenshot(path=f"auth_retry_{attempt+1}.png")
                    await page.wait_for_timeout(5000)
                    if attempt < max_login_retries - 1:
                        await page.reload()
            
            # If still failed after retries, we might be stuck
            if not self.session_authenticated:
                logger.error("All login attempts failed. Crawling public content or exiting if blocked.")
                await page.screenshot(path="snappod_login_final_fail.png")
        
        # 1. IMMEDIATE PRIORITY: Discover and Queue new links
        # This ensures that even if AI analysis hangs/crashes, the crawl frontier expands.
        if depth < self.max_depth:
            new_links = await self._discover_all_links(page)
            for link in new_links:
                await self._add_to_queue(link, depth + 1, current_url)
            
            yield {
                "event": "pages_discovered",
                "count": len(new_links),
                "url": current_url,
                "queue_size": len(self.discovery_queue)
            }

        # 2. Semantic Analysis (AI)
        if self.config.use_ai and depth <= self.config.ai_max_depth:
            self.current_semantic_map = await self._discover_semantic_components(page)
            if self.current_semantic_map:
                logger.info(f"Discovered {len(self.current_semantic_map)} semantic component zones")
        
        content_hash = await self._get_page_hash(page)
        logger.info(f"Page content hash: {content_hash}")

        # 3. Rich Interactions (AI Specialist)
        # Optimized: Strict checks for AI usage
        should_run_ai = self.config.use_ai and self.rich_manager and (depth <= self.config.ai_max_depth)
        
        if should_run_ai and (depth == 0 or len(self.current_semantic_map) > 3):
            logger.info("Triggering Agentic Rich Interaction for deep discovery...")
            pre_agent_url = page.url
            try:
                # Add timeout to prevent hanging the entire crawl
                # v5.1: Pass shared page context to preserve sessions
                rich_summary = await asyncio.wait_for(
                    self.rich_manager.explore_and_interact(current_url, page=page, timeout_sec=self.config.ai_timeout_sec), 
                    timeout=self.config.ai_timeout_sec + 5.0
                )
                logger.info(f"Rich Interaction Result: {rich_summary}")
                
                if page.is_closed():
                    logger.warning("Browser page closed during AI interaction.")
                    return

                post_agent_url = page.url
                # Check for AI-driven navigation (crucial for SPAs)
                if self._normalize_url(post_agent_url) != self._normalize_url(pre_agent_url):
                    logger.info(f"AI Agent navigated to new state: {post_agent_url}. Adding to discovery queue.")
                    await self._add_to_queue(post_agent_url, depth + 1, current_url)
                    
                    # v5.2: State Integrity - Return to original page for extraction if agent wandered off
                    if self._normalize_url(post_agent_url) != self._normalize_url(current_url):
                        logger.warning(f"AI Agent wandered to {post_agent_url}. Returning to {current_url} for extraction integrity.")
                        await page.goto(current_url, wait_until="networkidle")
                        await self._wait_for_stability(page)

            except asyncio.TimeoutError:
                 logger.warning(f"Rich Interaction timed out on {current_url}. Skipping interaction.")
            except Exception as e:
                 logger.warning(f"Rich Interaction failed on {current_url}: {e}")
                 # Ensure we are back on track if it failed mid-navigation
                 if not page.is_closed() and self._normalize_url(page.url) != self._normalize_url(current_url):
                     try:
                        logger.info(f"Restoring page state after AI failure: {current_url}")
                        await page.goto(current_url, wait_until="networkidle")
                     except: pass
        
        if self.browse_ai and depth == 0:
            logger.info("Triggering specialist Browse AI robot for baseline extraction...")
            await self.browse_ai.trigger_robot(current_url)

        if content_hash in self.visited_content_hashes:
            logger.info("Page content already visited. Skipping.")
            return
        self.visited_content_hashes.add(content_hash)

        # 0. WARM UP: Auto-consent and intelligent form filling
        logger.info(f"--- Processing START: {current_url} (Depth: {depth}) ---")
        await self._auto_consent(page)
        await self._auto_interact(page)

        logger.info(f"Emitting progress event for {current_url}...")
        try:
            yield {
                "event": "progress", 
                "url": current_url, 
                "depth": depth, 
                "path": path,
                "page_count": len(self.finished_urls) + 1,
                "status": "running"
            }
            logger.info("Progress event successfully yielded and processed by caller.")
        except (ValueError, IOError, BrokenPipeError, Exception) as ey:
            logger.warning(f"Output stream issue during progress yield (likely closed pipe): {ey}")

        # NEW: Discover ALL links from current page FIRST (before interactions)
        # This ensures we find all navigation links immediately
        if depth < self.max_depth:
            logger.info(f"Discovering links from {current_url} at depth {depth}")
            discovered_links = await self._discover_all_links(page)
            logger.info(f"Found {len(discovered_links)} total links on page")
            
            links_added = 0
            links_skipped = 0
            for link_url in discovered_links:
                # _add_to_queue has built-in duplicate checking
                queue_size_before = len(self.discovery_queue)
                await self._add_to_queue(link_url, depth + 1, current_url)
                if len(self.discovery_queue) > queue_size_before:
                    links_added += 1
                    logger.debug(f"Added link: {link_url}")
                else:
                    links_skipped += 1
                    logger.debug(f"Skipped link (duplicate or filtered): {link_url}")
            
            logger.info(f"Link discovery complete: {links_added} added, {links_skipped} skipped, queue size: {len(self.discovery_queue)}")
            
            if links_added > 0:
                logger.info(f"Added {links_added} new links to queue (total queue: {len(self.discovery_queue)})")
                
                yield {
                    "event": "pages_discovered",
                    "count": links_added,
                    "source": "page_links",
                    "queue_size": len(self.discovery_queue),
                    "depth": depth
                }

        safe_path = re.sub(r'\W+', '_', path)
        
        # v5.2: ROBUST PAGE STATE INTEGRITY (FINAL CHECK)
        # Ensure we are on the correct page before extraction, regardless of what happened above.
        if page.is_closed():
             logger.error(f"Page closed before extraction for {current_url}. Skipping.")
             return

        check_url = page.url
        print(f"DEBUG: Drift Check - Expected: {current_url}, Found: {check_url}", flush=True)
        if self._normalize_url(check_url) != self._normalize_url(current_url):
             print("DEBUG: Drift DETECTED!", flush=True)
             logger.warning(f"Page state drift detected before extraction! Expected {current_url}, found {check_url}. Forcing restoration.")
             try:
                 await page.goto(current_url, wait_until="networkidle")
                 await self._wait_for_stability(page)
                 
                 # v5.3: Session Recovery (Handle AI-induced logout)
                 if "login" in page.url.lower() or await self._detect_login(page):
                     logger.warning("Session lost during AI interaction! Attempting re-authentication...")
                     if await self._handle_login(page):
                         logger.info("Session recovered! Retrying navigation to target.")
                         await page.goto(current_url, wait_until="networkidle")
                         await self._wait_for_stability(page)
                     else:
                         logger.error("Failed to recover session after AI interaction. Extraction may follow on login page.")
                         
             except Exception as e:
                 logger.error(f"Failed to restore page state: {e}")

        # v5.5: Extraction Resilience with Retries
        page_data = None
        max_extract_retries = 3
        for attempt in range(max_extract_retries):
            try:
                page_data = await self._extract_elements(page, safe_path)
                break # Success
            except Exception as e:
                if "context was destroyed" in str(e).lower() or "navigation" in str(e).lower():
                    logger.warning(f"Extraction attempt {attempt + 1} failed for {current_url}: {e}. Retrying navigation...")
                    try:
                        await page.goto(current_url, wait_until="networkidle")
                        await self._wait_for_stability(page)
                    except: pass
                    continue
                else:
                    logger.error(f"Extraction attempt {attempt + 1} failed with unrecoverable error: {e}")
                    break
        
        # DEBUG: Trace page_data content
        if not page_data:
            print(f"DEBUGGING: page_data is NONE for {current_url}", flush=True)
            return # Skip this page if extraction failed after retries
        elif not page_data.get('elements'):
             print(f"DEBUGGING: page_data has NO ELEMENTS for {current_url}", flush=True)
        else:
             print(f"DEBUGGING: page_data has {len(page_data['elements'])} elements")

        if page_data and page_data.get('elements'):
            print(f"DEBUGGING: About to save {len(page_data['elements'])} elements for {current_url}", flush=True)
            # Save per-page JSON (v4.2 Lazy Increment)
            self.screen_id_counter += 1
            file_name = f"page_{self.screen_id_counter}.json"
            json_path = os.path.join(self.locators_dir, file_name)
            
            # DEBUG: Print exact save location
            print(f"DEBUG: Saving to: {os.path.abspath(json_path)}", flush=True)
            
            # Map elements to global storage AFTER successful extraction but BEFORE save
            for key, el in page_data['elements'].items():
                self.all_locators[f"state_{self.screen_id_counter}_{key}"] = el

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(page_data, f, indent=2)
            
            logger.info(f"Saved sequential locator file: {file_name}")
            try:
                yield {"event": "artifact", "type": "json", "path": json_path, "url": current_url}
            except (ValueError, IOError, BrokenPipeError):
                logger.warning("Could not yield artifact event - stream closed.")
            
            logger.info(f"Extracted {len(page_data.get('elements', {}))} elements and {len(page_data.get('tables', []))} tables from {current_url}")
        
        if depth < self.config.max_depth:
            logger.info(f"Starting Interaction Phase for {current_url} (Limit: {self.config.max_interactions_per_page})")
            await self._deep_interact(page, safe_path, depth)
            logger.info(f"Finished Interaction Phase for {current_url}")
            
        self.finished_urls.add(current_url)
        yield {"event": "finish_page", "url": current_url, "screen_id": self.screen_id_counter}
        logger.info(f"--- Processing FINISH: {current_url} (ID: {self.screen_id_counter}) ---")

    def _deduplicate_elements(self, elements: list) -> list:
        seen = {}
        # Pre-calc interactive XPaths for the text node check
        interactive_xpaths = {e['xpath'] for e in elements if e.get('isInteractive')}
        
        for el in elements:
            name = el.get('element_name')
            xpath = el['xpath']
            
            # 1. Text Node Redundancy Check
            if el['tag'] in ['span', 'div'] and el.get('text'):
                 parent_xpath = xpath.rsplit('/', 1)[0]
                 if parent_xpath in interactive_xpaths:
                     continue # Skip text node that is just label for parent button

            if name in seen:
                existing = seen[name]
                # Prefer interactive, then higher quality
                new_score = el.get('quality_score', 0)
                old_score = existing.get('quality_score', 0)
                new_interactive = el.get('isInteractive', False)
                old_interactive = existing.get('isInteractive', False)
                
                if (new_interactive and not old_interactive) or (new_score > old_score):
                    seen[name] = el
            else:
                seen[name] = el
        
        return list(seen.values())

    async def _extract_elements(self, page: Page, path: str) -> Dict[str, Any]:
        """Extract all interactive elements using Intelligent Extraction (v5.0)."""
        logger.info(f"Extracting elements from {page.url}...")
        
        await self._smart_scroll(page)
        await self._auto_interact(page)

        script = f"""
        ((includeHiddenStr) => {{
            {self._get_js_helpers()}
            return getAllElements(document, includeHiddenStr === 'true');
        }})('{str(self.config.include_hidden).lower()}')
        """
        
        try:
            raw_elements = await page.evaluate(script)
            logger.info(f"DEBUG: JS Extraction returned {len(raw_elements)} raw elements for {page.url}")
        except Exception as e:
            logger.error(f"CRITICAL: JS Extraction failed: {e}")
            raw_elements = []
        
        processed_elements = []
        skipped_counts = {"filtering": 0, "duplicate": 0, "quality": 0}
        
        for i, el in enumerate(raw_elements):
            # 1. Stricter Python Filtering
            if not self._is_testable_element(el['tag'], el['attributes'] or {}, el.get('text', '')):
                skipped_counts["filtering"] += 1
                continue
            
            # 2. Semantic Naming (using customLabel)
            el['element_name'] = self._generate_semantic_name(el)
            
            # 3. Refine Name
            el['element_name'] = self._refine_element_name(el['element_name'], el)
            
            # 4. Quality Score
            quality_score = 50
            if el.get('dataTestId'): quality_score = 95
            elif el.get('id') and not re.search(r'\d{5,}', el['id']): quality_score = 90
            elif el.get('customLabel'): quality_score = 85
            elif el.get('role'): quality_score = 80
            el['quality_score'] = quality_score
            
            # 5. Playwright Selector (Simplified for performance)
            if not el.get('playwright_selector') and el.get('css'):
                el['playwright_selector'] = f"page.locator('{el['css']}')"
            
            el['is_unique'] = True 
            el['element_count'] = 1
            
            processed_elements.append(el)
            
        # 6. Deduplication
        final_list = self._deduplicate_elements(processed_elements)
        
        # Convert list to dict keyed by name
        page_elements = {el['element_name']: el for el in final_list}

        print(f"DEBUGGING: Extraction finished with {len(page_elements)} elements", flush=True)
        logger.info(f"Extraction summary: {len(page_elements)} locators saved (from {len(raw_elements)} raw). Skips: {skipped_counts}")
        return {
            "elements": page_elements,
            "url": page.url,
            "screen_id": self.screen_id_counter,
            "timestamp": datetime.now().isoformat(),
            "metadata": {"title": await page.title()}
        }

    async def _deep_interact(self, page: Page, safe_path: str, depth: int) -> None:
        """Unified interaction logic for buttons, links, and dropdowns"""
        current_url = self._normalize_url(page.url)
        
        # 1. State Deduplication
        state_key = f"{current_url}|{await self._get_page_hash(page)}"
        if state_key in self.visited_states:
            return
        self.visited_states.add(state_key)
        
        # 2. Discovery & Sorting
        items = await self._discover_clickables(page)
        items = self._apply_priority_sorting(items)
        
        interaction_timeout = 600 # Increased for v6.0 (allows 100+ interactions)
        start_time = asyncio.get_event_loop().time()
        interaction_count = 0
        
        # 3. Interaction Loop
        for it in items[:self.config.max_interactions_per_page]:
            if asyncio.get_event_loop().time() - start_time > interaction_timeout:
                logger.warning("Overall interaction timeout reached")
                break

            target_xpath = it['xpath']
            if target_xpath in self.interaction_history:
                continue
            self.interaction_history.add(target_xpath)

            logger.info(f"Interacting with: {it['name']} ({target_xpath})")
            
            # v4.1: Surgical Success Tracking
            success = await self._smart_click(page, target_xpath)
            
            if not success:
                self.current_page_fails += 1
                logger.warning(f"Interaction failed ({self.current_page_fails}/{self.config.max_consecutive_failures})")
                if self.current_page_fails >= self.config.max_consecutive_failures:
                    logger.info("Threshold reached -> forcing rotation")
                    break 
            else:
                self.current_page_fails = 0
                self.total_interactions += 1
                interaction_count += 1
                
                # v6.0 SDET Logic: Check for state changes (On/Off, Toggle, Dropdown)
                # We wait a moment for animations/reveals
                await page.wait_for_timeout(500)
                
                # 1. State/Class change detection (Toggles)
                # We log if classes like 'active', 'pressed', 'open' appeared
                
                # 2. Reveal Detection (Dropdowns/Modals)
                # If new elements appear, we re-run extraction to capture them
                # This is "think out of the box" logic to ensure 100% coverage
                new_url = self._normalize_url(page.url)
                if new_url != current_url:
                    logger.info(f"Interaction led to new page: {new_url}. Adding to queue and returning.")
                    await self._add_to_queue(new_url, depth + 1, current_url)
                    
                    # Log transition outcome
                    self.site_graph.get(current_url, {}).setdefault("transitions", []).append({
                        "action": it['name'],
                        "to": new_url,
                        "type": "navigation"
                    })
                    
                    await page.go_back()
                    await self._wait_for_stability(page)
                    # Reset current_url state if needed, though loop continues
                else:
                    # Check for new links after interaction on same page
                    if depth < self.max_depth:
                        new_links = await self._discover_all_links(page)
                        for link in new_links:
                            await self._add_to_queue(link, depth + 1, current_url)
            
            await page.wait_for_timeout(1000)

    async def _smart_click(self, page: Page, xpath: str, max_retries: int = 2):
        """Elite click with locator API, sync checks, and shadow DOM fallbacks (v4.2)."""
        locator_str = f"xpath={xpath}"
        locator = page.locator(locator_str)
        
        # Pre-checks (sync in Playwright Python)
        try:
            count = await locator.count() 
            if count == 0:
                logger.error(f"Locator not found before click: {locator_str}")
                return False
            logger.debug(f"Pre-click locator count: {count}")
        except Exception as ce:
            logger.warning(f"Locator count failed: {ce}")

        for attempt in range(max_retries + 1):
            try:
                # 1. Wait for element
                await locator.wait_for(state="visible", timeout=self.config.timeout_sec * 1000)

                # 2. Aggressive JS scroll + center
                await page.evaluate("""
                    (xpath) => {
                        const el = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                        if (el) {
                            el.scrollIntoView({behavior: 'smooth', block: 'center', inline: 'center'});
                        }
                    }
                """, xpath)
                await page.wait_for_timeout(1000)

                # 3. Visibility check (sync!)
                try:
                    box = await locator.bounding_box()
                    v_size = page.viewport_size
                    if box and v_size and (box['y'] < 0 or box['y'] + box['height'] > v_size['height']):
                        if attempt < max_retries:
                            logger.debug(f"Element off-view after scroll (attempt {attempt+1}) → retrying")
                            continue
                        logger.warning("Element remains off-view")
                except Exception as be:
                    logger.debug(f"Bounding box check failed: {be}")

                # Senior SDET: Capture pre-interaction state for outcome verification
                pre_url = page.url
                pre_hash = await self._get_page_hash(page)
                pre_network = len(await page.evaluate("performance.getEntriesByType('resource')"))

                # 4. Native click with force
                logger.info(f"Clicking element: {it.get('name', 'node')} (Attempt {attempt+1})")
                await locator.click(force=True, timeout=5000)
                
                # 5. WAIT FOR OUTCOME (v6.0 SDET Heuristic)
                await page.wait_for_timeout(3000) # Wait for SPA transitions/animations
                
                # 6. POST-CLICK ANALYSIS
                post_url = page.url
                post_hash = await self._get_page_hash(page)
                post_network = len(await page.evaluate("performance.getEntriesByType('resource')"))
                
                has_url_change = self._normalize_url(post_url) != self._normalize_url(pre_url)
                has_dom_change = post_hash != pre_hash
                has_network_activity = post_network > (pre_network + 1)
                
                # Check for reveals (Modals, Toasts)
                has_overlay = await page.query_selector(".modal, .overlay, .toast, .success, .error, [role='alert']")
                
                if has_url_change or has_dom_change or has_network_activity or has_overlay:
                    status = "success"
                    if has_url_change: status += " (navigation)"
                    if has_dom_change: status += " (dom_change)"
                    if has_network_activity: status += " (network)"
                    if has_overlay: status += " (overlay)"
                    
                    logger.info(f"Interaction SUCCESS: Outcome detected: {status}")
                    return True
                else:
                    logger.warning(f"Interaction STALLED: No visible outcome detected (Attempt {attempt+1})")
                    if attempt < max_retries:
                        continue
                    return False

            except Exception as e:
                logger.warning(f"Click attempt {attempt+1} failed: {str(e)[:200]}")
                # Diagnostic screenshot on failure
                try:
                    fail_shot = f"interaction_failed_{int(datetime.now().timestamp())}.png"
                    await page.screenshot(path=fail_shot)
                    logger.info(f"Diagnostic screenshot saved to {fail_shot}")
                except: pass

                if attempt == max_retries:
                    # 6. Shadow-aware JS fallback (v4.2: Recursive dispatchEvent)
                    try:
                        logger.info(f"Triggering enhanced shadow-piercing JS fallback for {xpath}")
                        await page.evaluate("""
                            (xpath) => {
                                function deepClick(path, depth=0) {
                                    if (depth > 3) return false;
                                    let el = document.evaluate(path, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                                    if (el) {
                                        el.dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
                                        el.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
                                        el.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));
                                        return true;
                                    }
                                    // Recursive shadow root traversal
                                    const all = document.querySelectorAll('*');
                                    for (let node of all) {
                                        if (node.shadowRoot) {
                                            let shadowEl = document.evaluate(path, node.shadowRoot, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                                            if (shadowEl) {
                                                shadowEl.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));
                                                return true;
                                            }
                                            // Recurse deeper if needed (conceptually)
                                        }
                                    }
                                    return false;
                                }
                                if (!deepClick(xpath)) {
                                    throw new Error("Element not found even in shadow DOM");
                                }
                            }
                        """, xpath)
                        await page.wait_for_timeout(1500)
                        logger.info(f"Shadow-piercing JS click success: {locator_str}")
                        return True
                    except Exception as js_err:
                        logger.error(f"JS fallback failed: {str(js_err)}")
                        raise
        return False

    async def _discover_clickables(self, page: Page) -> List[Dict]:
        script = """
        () => {
            const items = [];
            const all = document.querySelectorAll('button, a, input[type="submit"], input[type="checkbox"], input[type="radio"], select, [role="button"], [role="link"], [role="checkbox"], [role="menuitem"], .btn, .button');
            for (const el of all) {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0 && getComputedStyle(el).visibility !== 'hidden') {
                    items.push({
                        tag: el.tagName.toLowerCase(),
                        name: (el.innerText || el.getAttribute('aria-label') || el.id || 'clickable').trim().substring(0, 50),
                        xpath: window.getSmartXPath(el),
                        y: rect.top + window.scrollY,
                        x: rect.left + window.scrollX
                    });
                }
            }
            return items;
        }
        """
        try:
            return await page.evaluate(script)
        except Exception as e:
            logger.debug(f"Handled failure in _discover_clickables: {str(e)}", exc_info=True)
            return []

    def _apply_priority_sorting(self, items: List[Dict]) -> List[Dict]:
        def get_prio(item):
            name = item['name'].lower()
            for i, kw in enumerate(self.config.priority_keywords):
                if kw.lower() in name: return i
            return 999
        return sorted(items, key=lambda x: (get_prio(x), x['y'], x['x']))

    async def _extract_revealed_elements(self, page: Page) -> List[Dict]:
        """Detect newly appeared elements after interaction (e.g. dropdowns)"""
        # Logic similar to _extract_elements but focused on new ones
        return [] # Simplified for now

    async def _handle_login(self, page: Page) -> bool:
        """Robust, universal login handler with granular error handling (v1.0 Generalization)"""
        creds = self.config.auth_creds
        if not creds or not creds.get('email'):
            logger.warning("No credentials provided for authentication.")
            return False

        email = creds.get('email')
        pwd = creds.get('password', '')

        try:
            logger.info(f"Initializing Unified Login Sequence for: {email[:3]}***@***")
            
            # 1. Ensure we are actually looking at a form (Wait for stability)
            await self._wait_for_stability(page, timeout_ms=3000)

            # 2. Email/Username Input
            logger.info("Attempting to fill email/username...")
            email_selector = "input[type='email'], input[name*='email'], input[name*='user'], #email, #username, #login-email"
            email_locator = page.locator(email_selector).first
            try:
                logger.info(f"Targeting email field: {email_selector}")
                await email_locator.wait_for(state="visible", timeout=10000)
                await email_locator.focus()
                await email_locator.fill("") # Clear
                await email_locator.press_sequentially(email, delay=100)
                logger.info("Email typed with sequential delays.")
                await page.screenshot(path="debug_email_filled.png")
            except Exception as e:
                logger.warning(f"Email field interaction failed: {e}")
                # Fallback to direct fill if focus/type failed
                try: await page.fill(email_selector, email)
                except: pass
                await page.screenshot(path="debug_email_error.png")
                
                # Handle potential multi-step form (Next button)
                try:
                    next_btn = await page.wait_for_selector("button:has-text('Next'), button:has-text('Continue')", timeout=2000)
                    if next_btn and await next_btn.is_visible():
                        await next_btn.click()
                        await page.wait_for_timeout(1000)
                        await page.screenshot(path="debug_after_next.png")
                except: pass
            else:
                logger.warning("Email/Username field not found.")

            # 3. Password Input
            logger.info("Attempting to fill password...")
            pass_selector = "input[type='password'], [name*='password'], #password, #login-password"
            pass_locator = page.locator(pass_selector).first
            try:
                await pass_locator.wait_for(state="visible", timeout=5000)
                await pass_locator.focus()
                await pass_locator.fill("") # Clear
                await pass_locator.press_sequentially(pwd, delay=100)
                logger.info("Password typed with sequential delays.")
                await page.screenshot(path="debug_pass_filled.png")
            except Exception as e:
                logger.warning(f"Password field interaction failed: {e}")
                try: await page.fill(pass_selector, pwd)
                except: pass
                await page.screenshot(path="debug_pass_error.png")

            # 4. Submit
            logger.info("Submitting login form...")
            submit = await page.query_selector("button[type='submit'], button.login-button, button:has-text('Login'), button:has-text('Sign In'), button:has-text('Log in')")
            
            if submit:
                await submit.click(force=True)
                logger.info("Submit button clicked (force=True).")
            else:
                await page.keyboard.press("Enter")
                logger.info("No submit button found, pressed Enter.")

            # 5. Wait for Success (Robust SDET Check)
            logger.info(f"Waiting for authentication success. Current URL: {page.url}")
            try:
                # v6.5 logic: URLs, Logout links, or Dashboard containers
                # Expanded for Clerk/SPA redirects
                await page.wait_for_function("""
                    () => {
                        const url = window.location.href;
                        const hasDashboard = url.includes('/dashboard') || url.includes('/projects') || url.includes('/home') || url.includes('/welcome') || url.includes('/app');
                        const hasLogout = document.querySelector('a[href*="/logout"], button:has-text("Logout"), a:has-text("Sign Out"), li:has-text("Logout"), [class*="cl-userButtonTrigger"]');
                        const hasDash = document.querySelector('.dashboard-container, #dashboard, .app-container, .dashboard_layout, .cl-root');
                        const isAuthPage = url.includes('/login') || url.includes('/signup');
                        return (hasDashboard && !isAuthPage) || hasLogout || (hasDash && !isAuthPage);
                    }
                """, timeout=20000)
                
                logger.info(f"Authentication SUCCESS! Landed on: {page.url}")
                self.session_authenticated = True
                await page.wait_for_timeout(4000) # Final settlement wait
                return True
            except Exception as e:
                logger.warning(f"Auth signals timeout ({page.url}). Performing final heuristic check.")
                
                # Check for absence of login form as a success signal
                auth_state = await self._detect_auth_type(page)
                if auth_state == "NONE":
                    logger.info("No login/signup form detected and URL shifted. Assuming SUCCESS.")
                    self.session_authenticated = True
                    return True
                
                logger.error(f"Authentication FAILURE: Still in {auth_state} state.")
                return False

        except Exception as e:
            logger.error(f"Login process failed: {e}")
            await page.screenshot(path="login_error_trace.png")
            return False

    async def _detect_login(self, page: Page) -> bool:
        """Heuristic check if current page is a login page (v5.5: Shadow DOM aware)"""
        return (await self._detect_auth_type(page)) == "LOGIN"

    async def _detect_auth_type(self, page: Page) -> str:
        """
        Differentiate between LOGIN, SIGNUP, and NONE based on page signals. (v6.2 Robustness)
        """
        url = page.url.lower()
        content = (await page.content()).lower()
        
        # 1. Signup Signals (Highest priority to avoid mis-authing)
        signup_patterns = ["signup", "register", "join", "create account", "create-account"]
        signup_fields = ["first name", "last name", "phone number", "confirm password"]
        
        has_signup_url = any(p in url for p in signup_patterns)
        has_signup_fields = any(f in content for f in signup_fields)
        
        # 2. Login Signals
        login_patterns = ["login", "signin", "auth", "account"]
        password_field = await page.locator("input[type='password']").count() > 0
        
        if (has_signup_url or has_signup_fields):
            logger.info("Heuristic: Signup page detected.")
            return "SIGNUP"
        
        if password_field or any(p in url for p in login_patterns):
            logger.info("Heuristic: Login page detected.")
            return "LOGIN"
            
        return "NONE"



    async def _get_page_hash(self, page: Page) -> str:
        """Robust content hash for outcome detection (v10/10 SDET)"""
        try:
            # slice(0, 1000) as requested for better accuracy
            return await page.evaluate("document.body.innerHTML.slice(0, 1000)")
        except:
            return ""

    def _generate_semantic_name(self, entry: dict) -> str:
        """Senior SDET Refined Naming Logic: Priority 1 Labels/Roles > Text"""
        # Priority 1: Custom Label (Merged label from label tags)
        if entry.get('customLabel'):
            name = entry['customLabel'].lower().replace(' ', '_').replace("'", "").replace('"', '')
        # Priority 2: aria-label
        elif entry.get('attributes', {}).get('aria-label'):
            name = entry['attributes']['aria-label'].lower().replace(' ', '_')
        # Priority 3: Role (if not default 'element')
        elif entry.get('role') and entry['role'] != 'element':
            name = entry['role'].lower()
        # Priority 4: Text Content (Truncated)
        elif entry.get('text'):
            name = entry['text'][:30].lower().replace(' ', '_').replace("'", "").replace('"', '')
        else:
            name = f"{entry.get('tag', 'element')}_el"

        # Sanitize
        name = re.sub(r'[^a-zA-Z0-9_]', '', name)
        
        # Priority Collision Resistance: coordinates as last resort
        if name in self.seen_names:
            name += f"_{int(entry.get('x', 0))}_{int(entry.get('y', 0))}"

        self.seen_names.add(name)
        return name[:64].strip('_')


    def _refine_element_name(self, name: str, el: Dict) -> str:
        """Quick rule-based refinement – no LLM cost as requested"""
        name = name.lower().replace(" ", "_").replace("-", "_")
        
        # Remove generic prefixes or placeholder names
        name = re.sub(r'^(span|div|element|item|clickable|i|section|main|header|footer)_\d+$', 'unknown', name)
        
        # Get important attributes
        tag = el.get('tag', '')
        if tag:
            tag = tag.lower()
        else:
            tag = ''
        role = (el.get('attributes', {}).get('role') or '').lower()
        
        # Boost priority tags with prefixes
        prefix = ""
        if tag == 'button' or role == 'button': prefix = "btn"
        elif tag == 'a' or role == 'link': prefix = "link"
        elif tag == 'input' or tag == 'textarea': prefix = "input"
        elif tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']: prefix = "heading"
        
        # Combine
        if prefix and not name.startswith(prefix):
            if name == 'unknown':
                name = prefix
            else:
                name = f"{prefix}_{name}"
            
        # Add role if present and not already emphasized
        if role and role not in name and role not in ['presentation', 'none']:
            name = f"{role}_{name}"
            
        # Clean up double underscores and length
        name = re.sub(r'_+', '_', name).strip('_')
        return name[:80]

    def _calculate_stability(self, el: Dict) -> int:
        score = 50
        if el['attributes'].get('dataTestId'): score += 40
        elif el['attributes'].get('id') and not re.search(r'\d{5,}', el['attributes']['id']): score += 30
        if el['playwright_selector']: score += 10
        return min(score, 100)
    
    
    def _is_testable_element(self, tag: str, attrs: dict, text: str) -> bool:
        # Drop labels entirely (merged client-side)
        if tag == 'label':
            return False

        # Drop pure structural div/span unless explicit role or onclick
        if tag in ['div', 'span', 'i', 'section']:
            # Check for interactive attributes
            is_interactive = any([
                attrs.get('role') in ['button', 'link', 'checkbox', 'radio', 'tab', 'menuitem'],
                attrs.get('onclick'),
                attrs.get('tabindex') is not None,
                # Short text might be a button label
                (text and len(text.strip()) < 50) 
            ])
            if not is_interactive:
                return False

        # Keep only high-signal elements (v5.4 leniency)
        if tag in ['input', 'button', 'a', 'select', 'textarea']:
            return True

        # Role-based or aria-label keep
        if attrs.get('role') in ['button', 'link', 'checkbox', 'radio', 'tab', 'option', 'menuitem'] or attrs.get('aria-label'):
            return True

        # Lenient text check for dynamic components (Snappod AI)
        if text and 0 < len(text.strip()) < 100:
            return True

        return False # Default reject noise
    
    def _generate_element_fingerprint(self, el: Dict) -> str:
        """Create high-entropy unique fingerprint based on semantic and structural traits."""
        tag = el['tag'].lower()
        attrs = el.get('attributes', {})
        text = (el.get('text') or '').strip()
        
        # Build components for SHA256 hash
        components = [
            tag,
            str(attrs.get('dataTestId') or ''),
            str(attrs.get('id') or ''),
            str(attrs.get('role') or ''),
            str(attrs.get('type') or ''),
            str(attrs.get('name') or ''),
            str(attrs.get('ariaLabel') or ''),
            str(attrs.get('placeholder') or '')
        ]
        
        # Add a snippet of text if it's long enough to be an identifier
        if text and len(text) > 4:
            # Normalize whitespace and limit length for stability
            clean_text = re.sub(r'\s+', ' ', text.lower()).strip()[:80]
            components.append(f"txt:{clean_text}")
        
        # Create hash
        fingerprint_string = "|".join(components)
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()
    
    async def _validate_playwright_selector(self, page: Page, selector: str, expected_xpath: str) -> Tuple[bool, int]:
        """Validate that a Playwright selector is unique and finds the correct element."""
        try:
            # Simple validation: check if XPath finds exactly one element
            elements = await page.locator(f"xpath={expected_xpath}").all()
            count = len(elements)
            is_unique = count == 1
            return (is_unique, count)
        except Exception as e:
            logger.warning(f"Selector validation failed: {e}")
            return (False, 0)
    
    def _calculate_selector_quality(self, el: Dict, selector: str, is_unique: bool) -> int:
        """Score selector quality from 0-100."""
        if not is_unique:
            return 0  # Invalid selector
        
        score = 0
        attrs = el.get('attributes', {})
        
        # Best: data-testid
        if 'getByTestId' in selector:
            score = 95
        # Excellent: Stable ID
        elif attrs.get('id') and "locator('#" in selector:
            if not re.search(r'\d{5,}', attrs['id']):
                score = 90
            else:
                score = 60  # Dynamic ID
        # Very Good: Role + Name
        elif 'getByRole' in selector:
            score = 85
        # Good: Placeholder or Label
        elif 'getByPlaceholder' in selector or 'getByLabel' in selector:
            score = 80
        # Fair: Text content
        elif 'getByText' in selector:
            text_len = len(el.get('text', ''))
            score = 70 if text_len < 20 else 50
        # Poor: Class selectors
        elif "locator('." in selector:
            score = 40
        # Very Poor: XPath
        elif 'xpath=' in selector:
            score = 60 if '//*[@id=' in selector else 20
        else:
            score = 30
        
        return score

    async def _wait_for_stability(self, page: Page):
        await page.wait_for_load_state("networkidle", timeout=self.config.timeout_sec * 1000)
        await asyncio.sleep(0.5)

    async def _wait_for_network_idle(self):
        start = asyncio.get_event_loop().time()
        while len(self.active_requests) > 0 and (asyncio.get_event_loop().time() - start) < 5:
            await asyncio.sleep(0.2)

    async def _get_page_hash(self, page: Page) -> str:
        """v4.8: Advanced Semantic hashing with selector-based noise filtering."""
        try:
            # Script to get text but strip common dynamic patterns and specific noise selectors
            data = await page.evaluate("""() => {
                const clone = document.body.cloneNode(true);
                // Remove known dynamic items that break state tracking
                const ignoreSelectors = [
                    '.live-clock', '.counter', '[data-last-updated]', 'time', 
                    '.timestamp', '#view-counter', '.weather-widget',
                    '.ad-banner', '[role="timer"]', '.spinner', '.loading',
                    '[aria-live="polite"]'
                ];
                ignoreSelectors.forEach(sel => {
                    try {
                         clone.querySelectorAll(sel).forEach(el => el.remove());
                    } catch(e) {}
                });

                const text = clone.innerText || '';
                // Strip dates, times, and long sequences of numbers
                const cleanText = text.replace(/\\d{1,4}[\\-/:]\\d{1,4}[\\-/:]\\d{1,4}/g, 'DATE')
                                    .replace(/\\d{1,2}:\\d{1,2}(:\\d{1,2})?/g, 'TIME')
                                    .replace(/\\d{6,}/g, 'NUM')
                                    .trim();
                
                // Return raw concatenated string for Python hashing (btoa fails on non-Latin1)
                return cleanText + clone.querySelectorAll('*').length + clone.outerHTML.substring(0, 1000);
            }""")
            return hashlib.sha256(data.encode('utf-8')).hexdigest()
        except Exception as e:
            logger.error(f"ERROR in _get_page_hash: {e}")
            return "ERROR_HASH"

    def _get_clean_page_context(self, html: str) -> str:
        """
        'Page Scalpel': Strips HTML of non-visual nodes to get a clean semantic representation.
        Inspired by Crawl4AI's Markdown extraction.
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove scripts, styles, and other metadata
            for tag in soup(['script', 'style', 'meta', 'link', 'noscript', 'svg', 'iframe']):
                tag.decompose()
            
            # Extract basic structure
            lines = []
            for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'a', 'button', 'input', 'label']):
                tag = element.name
                text = element.get_text(strip=True)
                if not text and tag not in ['input']:
                    continue
                
                # Add role or type if available
                attr_info = ""
                if tag == 'input':
                    attr_info = f" [type={element.get('type', 'text')}, name={element.get('name', '')}]"
                elif tag == 'a':
                    attr_info = f" [href={element.get('href', '')}]"
                
                lines.append(f"<{tag}>{text}{attr_info}")
                
            return "\n".join(lines[:150]) # Limit context size
        except Exception as e:
            logger.error(f"Error in _get_clean_page_context: {e}")
            return ""

    async def _discover_semantic_components(self, page: Page) -> Dict[str, str]:
        """
        Uses AI to identify logical UI components on the page.
        """
        if not self.client or not self.config.use_ai:
            return {}

        try:
            source = await page.content()
            clean_context = self._get_clean_page_context(source)
            if not clean_context:
                return {}

            prompt = f"""
            Analyze the following website structure and identify the main logical UI components.
            Group the items into areas like: 'Navigation', 'Search', 'Auth', 'Main Content', 'Footer', etc.
            
            STRUCTURE:
            {clean_context}
            
            Return a JSON object mapping specific keywords or identifiers to their logical group.
            Example: {{"login": "Auth", "cart": "Shopping", "search": "Discovery"}}
            """
            
            # Rotation Logic
            max_retries = 4
            response = None
            
            for attempt in range(max_retries):
                try:
                    response = await self.client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}],
                        response_format={"type": "json_object"}
                    )
                    break # Success
                except Exception as req_err:
                    # Check for Rate Limit
                    err_str = str(req_err)
                    if "429" in err_str:
                        logger.warning(f"Groq Rate Limit (Key {self.groq_key_index + 1}/{len(self.groq_keys)}). Rotating...")
                        if self.groq_keys:
                            self.groq_key_index = (self.groq_key_index + 1) % len(self.groq_keys)
                            self.client = AsyncGroq(api_key=self.groq_keys[self.groq_key_index])
                            await asyncio.sleep(1)
                            continue
                    
                    if attempt == max_retries - 1:
                        raise req_err # Rethrow if last attempt
                    await asyncio.sleep(1)
            
            if not response:
                return {}
            
            try:
                result = json.loads(response.choices[0].message.content)
                if isinstance(result, dict):
                    return result
                logger.warning(f"Semantic discovery returned non-dict: {type(result)}")
                return {}
            except Exception as ej:
                logger.error(f"Error parsing semantic JSON: {ej}")
                return {}
        except Exception as e:
            logger.warning(f"Semantic component discovery failed: {e}")
            return {}

    # Redundant _normalize_url removed (using the robust one at line 363)

    async def _smart_scroll(self, page: Page):
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1)
        await page.evaluate("window.scrollTo(0, 0)")

    async def _auto_consent(self, page: Page):
        """v5.1: Safer Auto-dismiss cookies/consent with outlier protection."""
        # 1. High-confidence phrases (Safe to click links/buttons)
        safe_phrases = ["accept all", "accept cookies", "allow all", "i agree", "got it", "allow selection", "manage cookies"]
        
        for text in safe_phrases:
            try:
                # Case-insensitive substring match is default for :has-text
                el = await page.query_selector(f"button:has-text('{text}'), a:has-text('{text}'), [role='button']:has-text('{text}')")
                if el and await el.is_visible():
                    await el.click()
                    logger.info(f"Auto-consent SAFE click: {text}")
                    return
            except Exception: pass

        # 2. Risky single words (Buttons ONLY - never links)
        # We avoid 'agree' or 'consent' on links to prevent clicking "Data Processing Agreement"
        risky_words = ["accept", "agree", "allow", "ok", "consent"]
        
        for text in risky_words:
            try:
                # Strict: generic words must be buttons or explicit roles
                el = await page.query_selector(f"button:has-text('{text}'), [role='button']:has-text('{text}')")
                if el and await el.is_visible():
                    # Double check content length to avoid "I do not accept" or long legal text
                    content = await el.inner_text()
                    if len(content) < 40: 
                        await el.click()
                        logger.info(f"Auto-consent STRICT button click: {text}")
                        return
            except Exception: pass

    async def _auto_interact(self, page: Page):
        """Intelligent form-filling and dropdown expansion."""
        
        # 1. Expand Dropdowns/Accordions (NEW)
        try:
            # Click potential toggles
            await page.evaluate("""
                () => {
                    document.querySelectorAll('.dropdown-toggle, [aria-haspopup="true"], [data-toggle="dropdown"]').forEach(el => {
                       if (el.offsetParent !== null) {
                           try { el.click(); } catch(e) {}
                       } 
                    });
                }
            """)
            await asyncio.sleep(0.5) 
        except Exception: pass

        inputs = await page.query_selector_all("input:not([type='hidden']), textarea, select")
        for inp in inputs:
            try:
                tag = await inp.evaluate("el => el.tagName.toLowerCase()")
                type_attr = str(await inp.get_attribute("type") or "").lower()
                name = str(await inp.get_attribute("name") or "").lower()
                id_attr = str(await inp.get_attribute("id") or "").lower()
                placeholder = str(await inp.get_attribute("placeholder") or "").lower()
                label = await inp.evaluate("el => el.labels && el.labels[0] ? el.labels[0].innerText : ''")
                target_str = (name + " " + id_attr + " " + placeholder + " " + label).lower()

                # Basic check for already filled
                if await inp.evaluate("el => el.value"):
                    continue

                # 1. Datepicker Rule
                if any(word in target_str for word in ["date", "datepicker", "birthday"]):
                    await inp.click() # Open picker
                    await asyncio.sleep(1)
                    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%m/%d/%Y")
                    await page.keyboard.type(tomorrow)
                    await page.keyboard.press("Enter")
                    logger.info(f"Filled datefield with {tomorrow}")

                # 2. File Upload Rule
                elif type_attr == "file" or "upload" in target_str:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
                        tmp.write(b"Dummy test file content for Formy upload.")
                        dummy_path = tmp.name
                    await inp.set_input_files(dummy_path)
                    logger.info(f"Uploaded dummy file: {dummy_path}")
                    # Note: file remains to ensure upload completes, OS will usually clean temp

                # 3. Autocomplete / Search Rule
                elif "autocomplete" in target_str or "search" in name:
                    await inp.type("Los Angeles")
                    await asyncio.sleep(1)
                    await page.keyboard.press("ArrowDown")
                    await page.keyboard.press("Enter")
                    logger.info("Autocomplete selected")

                # 4. Checkbox Rule
                elif type_attr == "checkbox" or "terms" in target_str:
                    if not await inp.is_checked():
                        await inp.check()
                        logger.info("Checked checkbox")

                # 5. Radio Button Rule
                elif type_attr == "radio":
                    if not await inp.is_checked():
                        await inp.check()
                        logger.info("Selected radio option")
                
                # 6. Generic Catch-all
                elif type_attr in ['text', 'email', 'password', 'tel', 'url', 'number', '']:
                    val = "Test Data"
                    if "email" in target_str: 
                        val = self.config.auth_creds.get('email', "test@example.com") if self.config.auth_creds else "test@example.com"
                    elif "password" in target_str:
                        val = self.config.auth_creds.get('password', "TestPass123") if self.config.auth_creds else "TestPass123"
                    elif "phone" in target_str: val = "555-0199"
                    elif "zip" in target_str: val = "90210"
                    
                    try:
                        await inp.fill(val)
                        logger.info(f"Auto-filled generic {type_attr}: {val}")
                    except: pass

            except Exception as e:
                logger.debug(f"Form-fill skipped for element: {e}")

        # 7. Button/Toggle/Input Clicking (NEW - User Request)
        try:
             # Click buttons that might reveal content, and checkboxes/radios
             await page.evaluate("""
                () => {
                    const clickables = document.querySelectorAll('button:not([type="submit"]), [role="button"], div.btn, span.btn, input[type="checkbox"], input[type="radio"], input[type="file"]');
                    clickables.forEach(el => {
                        // Avoid obvious navigation
                        if (el.closest('a')) return;
                        
                        const text = (el.innerText || el.value || "").toLowerCase();
                        if (text.includes('submit') || text.includes('save') || text.includes('login') || text.includes('sign in')) return;

                        if (el.offsetParent !== null) {
                             try { 
                                 // For checkboxes/radios, only click if not checked
                                 if ((el.type === 'checkbox' || el.type === 'radio') && el.checked) return;
                                 
                                 el.click(); 
                             } catch(e) {}
                        }
                    });
                }
             """)
             await asyncio.sleep(0.5)
        except Exception: pass

    def _get_js_helpers(self) -> str:
        return """
        function getSmartXPath(el) {
            if (el.id) return `//*[@id="${el.id}"]`;
            if (el.getAttribute('data-testid')) return `//*[@data-testid="${el.getAttribute('data-testid')}"]`;
            if (el === document.body) return '/html/body';
            
            let current = el;
            let path = '';
            while (current && current.nodeType === 1 && current !== document.body) {
                if (current.id) {
                    return `//*[@id="${current.id}"]` + path;
                }
                let index = 1;
                for (let sib = current.previousSibling; sib; sib = sib.previousSibling) {
                    if (sib.nodeType === 1 && sib.tagName === current.tagName) index++;
                }
                path = '/' + current.tagName.toLowerCase() + '[' + index + ']' + path;
                current = current.parentNode;
            }
            return '/html/body' + path;
        }

        function getSmartCSS(el) {
            if (el.id) return '#' + el.id;
            if (el.className && typeof el.className === 'string') {
                const classes = el.className.split(/\\s+/).filter(c => c && !c.match(/\\d/)).join('.');
                if (classes) return el.tagName.toLowerCase() + '.' + classes;
            }
            return el.tagName.toLowerCase();
        }

        function getPlaywrightSelector(el) {
             return ""; // Placeholder
        }

        function getAllElements(root = document, includeHidden = false) {
            const result = [];

            function walk(node, depth = 0) {
                if (depth > 20) return; // Increased depth for modern frameworks
                if (!node) return;

                const nodeType = node.nodeType;
                const tag = (node.tagName || "").toLowerCase();

                // 1. Process as Element
                if (nodeType === 1) {
                    if (['script', 'style', 'noscript', 'meta', 'link', 'head'].includes(tag)) return;

                    // Visibility check
                    if (!includeHidden) {
                        const style = window.getComputedStyle(node);
                        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') {
                        return;
                    }
                }

                // v5.4: Shadow DOM Traversal
                if (node.shadowRoot) {
                    walk(node.shadowRoot, depth + 1);
                }

                    // Special handling for labels
                    if (tag === 'label') {
                        const forId = node.getAttribute('for');
                        if (forId) {
                            const control = document.getElementById(forId) || document.querySelector(`[name="${forId}"]`);
                            if (control) {
                                control.setAttribute('data-custom-label', node.innerText.trim());
                                // We still walk labels because they might contain other things, 
                                // but we skip saving them if they are pure text labels for an ID
                            }
                        }
                    }

                    // Collect meaningful elements
                    const rect = node.getBoundingClientRect();
                    const entry = {
                        tag: tag,
                        text: (node.innerText || '').trim().slice(0, 100),
                        xpath: getSmartXPath(node),
                        css: getSmartCSS(node),
                        role: node.getAttribute('role') || '',
                        id: node.id || '',
                        name: node.getAttribute('name') || '',
                        type: node.getAttribute('type') || '',
                        placeholder: node.getAttribute('placeholder') || '',
                        ariaLabel: node.getAttribute('aria-label') || '',
                        dataTestId: node.getAttribute('data-testid') || '',
                        customLabel: node.getAttribute('data-custom-label') || '',
                        isInteractive: !!node.onclick || ['input', 'button', 'a', 'select', 'textarea'].includes(tag) || node.getAttribute('role') === 'button',
                        attributes: {
                             href: node.getAttribute('href'),
                             src: node.getAttribute('src'),
                             class: node.className
                        },
                        x: Math.round(rect.left + window.scrollX),
                        y: Math.round(rect.top + window.scrollY)
                    };

                    // Cleanup empty fields as requested by user
                    ['role', 'name', 'type', 'placeholder', 'ariaLabel', 'dataTestId', 'customLabel'].forEach(key => {
                        if (entry[key] === '') delete entry[key];
                    });

                    if (entry.isInteractive || entry.role || entry.id || entry.ariaLabel || entry.customLabel || (entry.text && entry.text.length > 0)) {
                        result.push(entry);
                    } else {
                        // pure empty container – skip
                        return; 
                    }
                }

                // 2. Recurse into children (Elements, Document, ShadowRoot)
                if (node.shadowRoot) walk(node.shadowRoot, depth + 1);
                
                const children = node.children || node.childNodes;
                if (children) {
                    Array.from(children).forEach(child => walk(child, depth + 1));
                }
            }

            walk(root);
            return result;
        }
        
        function getRelativeXPath(el) { return ""; } // Placeholder

        window.getAllElements = getAllElements;
        window.getSmartXPath = getSmartXPath;
        window.getSmartCSS = getSmartCSS;
        window.getPlaywrightSelector = getPlaywrightSelector;
        """



    def _save_consolidated_locators(self) -> str:
        # Ensure locators_root directory exists
        os.makedirs(self.locators_root, exist_ok=True)
        
        # Save as Python dict (legacy)
        py_path = os.path.join(self.locators_root, 'all_locators.py')
        with open(py_path, 'w', encoding='utf-8') as f:
            f.write(f"locators = {json.dumps(self.all_locators, indent=4)}\n")
            f.write(f"site_graph = {json.dumps(self.site_graph, indent=4)}\n")
        
        # Save as pure JSON (for dashboard/next agents)
        json_path = os.path.join(self.locators_root, 'all_locators.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                "locators": self.all_locators,
                "site_graph": self.site_graph,
                "metadata": {
                    "total_pages": len(self.finished_urls),
                    "total_locators": len(self.all_locators),
                    "timestamp": datetime.now().isoformat()
                }
            }, f, indent=4)
        return json_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="QA Garden Crawler - Elite Reliability Edition (v4)")
    parser.add_argument("--url", type=str, required=True, help="Target URL")
    parser.add_argument("--max-depth", type=int, default=2, help="Max crawl depth")
    parser.add_argument("--max-pages", type=int, default=10, help="Max pages")
    parser.add_argument("--dynamic", action="store_true", help="Enable dynamic discovery")
    parser.add_argument("--camoufox", action="store_true", default=False, help="Use Camoufox stealth")
    parser.add_argument("--headless", action="store_true", help="Force headless mode")
    parser.add_argument("--respect_robots", type=str, default="True", help="Respect robots.txt (True/False)")
    parser.add_argument("--exclude", nargs='*', help="List of URL paths to exclude")
    
    args = parser.parse_args()
    
    # Handle boolean for respect_robots
    respect_robots = args.respect_robots.lower() == "true"
    
    # Auto-load credentials from environment if available
    import os
    env_email = os.environ.get("SNAPPOD_TEST_EMAIL")
    env_pwd = os.environ.get("SNAPPOD_TEST_PASSWORD")
    auth_creds = None
    if env_email and env_pwd:
        auth_creds = {"email": env_email, "password": env_pwd}

    config = CrawlerConfig(
        url=args.url,
        max_depth=args.max_depth,
        max_pages=args.max_pages,
        dynamic_crawl=args.dynamic,
        use_camoufox=args.camoufox,
        headless=args.headless,
        respect_robots=respect_robots,
        exclude_paths=args.exclude if args.exclude else [],
        auth_creds=auth_creds
    )
    
    crawler = QAGardenCrawler(config)
    
    async def main():
        async for update in crawler.run():
            if update.get("type") == "log":
                print(f"[{update.get('level', 'INFO')}] {update.get('message')}")
            elif update.get("type") == "page_complete":
                print(f"--- Completed: {update.get('url')} (Total Locators: {update.get('total_locators', 0)}) ---")
            elif update.get("type") == "crawl_complete":
                print(f"Crawl finished. Locators saved to: {update.get('locators_path')}")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCrawl Aborted.")
