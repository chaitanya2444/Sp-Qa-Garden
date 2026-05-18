from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Literal

class CrawlerConfig(BaseModel):
    url: str = Field(..., description="Target URL to crawl (must be http/https)")
    max_depth: int = Field(default=4, ge=0, descriptions="Maximum crawl depth")
    max_pages: int = Field(default=30, ge=1, description="Maximum number of pages to crawl")
    interaction_timeout: int = Field(default=60, description="Timeout for interactions in ms")
    max_consecutive_failures: int = Field(default=3, description="Max consecutive nav failures before rotation")
    max_consecutive_interaction_failures: int = Field(default=8, description="Max consecutive interaction failures before rotation")
    auth_creds: Optional[Dict[str, str]] = Field(default=None, description="Optional login credentials (email, password)")
    priority_keywords: List[str] = Field(default_factory=list, description="Keywords to prioritize for navigation")
    use_ai: bool = Field(default=False, description="Enable AI-driven naming and navigation (requires GROQ_API_KEY)")
    timeout_sec: int = Field(default=45, ge=5, description="Network timeout in seconds")
    max_retries: int = Field(default=3, ge=0, description="Number of retries for failed requests")
    failure_policy: Literal["stop", "continue", "retry"] = Field(default="continue", description="Action on failure")
    headless: bool = Field(default=True, description="Run browser in headless mode")
    include_hidden: bool = Field(default=False, description="Extract hidden elements")
    job_id: Optional[str] = Field(default=None, description="Job ID for tracking progress")
    enable_site_mapping: bool = Field(default=True, description="Enable proactive site discovery (mapping)")
    sitemap_enabled: bool = Field(default=True, description="Enable sitemap.xml parsing")
    firecrawl_api_key: Optional[str] = Field(default=None, description="Firecrawl API key for enhanced mapping")
    max_interactions_per_page: int = Field(default=6, ge=1, description="Maximum interactions per page to prevent loops")
    respect_robots: bool = Field(default=True, description="Respect robots.txt rules (disable for testing only)")
    enable_rich_interactions: bool = Field(default=True, description="Enable autonomous discovery with browser-use")
    browse_ai_enabled: bool = Field(default=False, description="Enable specialist extraction with Browse AI robots")
    ai_max_depth: int = Field(default=1, ge=0, description="Max depth to run expensive AI analysis")
    ai_timeout_sec: int = Field(default=60, ge=10, description="Hard timeout for AI agent steps/interaction")
    strict_element_filtering: bool = Field(default=True, description="Enable stricter filtering for better data quality")
    dynamic_crawl: bool = Field(default=False, description="Allow crawling outside the starting domain")
    site_specific_locators: bool = Field(default=True, description="Store locators in site-specific subdirectories")
    max_crawl_duration_sec: int = Field(default=1800, ge=60, description="Hard timeout for the entire crawl job")
    viewport_width: int = Field(default=1280, ge=320, description="Browser viewport width")
    viewport_height: int = Field(default=800, ge=240, description="Browser viewport height")
    table_extraction_limit: int = Field(default=10, ge=1, description="Max rows to extract from a single table to prevent bloat")
    context_rotation_mem_threshold: float = Field(default=98.0, ge=50, le=99, description="Memory percentage threshold to trigger rotation")
    mobile_emulation: bool = Field(default=False, description="Whether to emulate a mobile device")
    random_viewport: bool = Field(default=True, description="Whether to randomize viewport slightly to bypass detection")
    browserbase_keepalive: bool = Field(default=False, description="Whether to use Browserbase native keepAlive (paid plans only)")
    use_camoufox: bool = Field(default=False, description="Use local Camoufox stealth browser (Firefox-based)")
    camoufox_fingerprint_preset: Literal["realistic", "aggressive_random", "custom"] = Field(default="realistic", description="Fingerprint generation mode for Camoufox")
    camoufox_headless_mode: Literal["true", "false", "virtual"] = Field(default="virtual", description="Headless mode (virtual is best for stealth)")
    force_headless_on_windows: bool = Field(default=False, description="Force headless even on Windows (reduces stealth/debuggability)")
    auto_revert_headful: bool = Field(default=True, description="Auto-revert to headless after several successful pages")
    max_queue_size: int = Field(default=5000, ge=100, description="Maximum number of URLs in discovery queue")
    state_hash_noise_threshold: int = Field(default=5, ge=0, description="Similarity threshold for state deduplication")
    exclude_paths: List[str] = Field(default_factory=list, description="List of URL path substrings to exclude")
    
    # Phase 1: Modular Patterns
    exclude_marketing_keywords: List[str] = Field(
        default_factory=lambda: ["pricing", "plans", "features", "about", "blog", "contact", "use-cases", "customers"],
        description="Keywords to filter out marketing pages in authenticated sessions"
    )
    login_url_patterns: List[str] = Field(
        default_factory=lambda: ["/login", "/signin", "/auth", "/account"],
        description="Common URL patterns identifying login pages"
    )
    marketing_url_patterns: List[str] = Field(
        default_factory=list, 
        description="Site-specific marketing URL patterns"
    )
