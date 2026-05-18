#!/usr/bin/env python3
import asyncio
import os
import argparse
from typing import Optional

# Switch to the new AI-augmented crawler
from qa_garden_crawler import QAGardenCrawler
from config import CrawlerConfig

from dotenv import load_dotenv
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="QA Garden Crawler: AI-Augmented Web Explorer")
    parser.add_argument("urls", nargs='*', help="Target URLs to crawl (optional if TARGET_URL is in .env)")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode", default=True)
    parser.add_argument("--no-headless", action="store_false", dest="headless", help="Run in headful mode")
    parser.add_argument("--max-pages", type=int, default=50, help="Maximum pages to crawl")
    parser.add_argument("--depth", type=int, default=3, help="Maximum crawl depth")
    
    # New Arguments for Optimization
    parser.add_argument("--use-ai", action="store_true", help="Enable AI-driven interaction (costs tokens)")
    parser.add_argument("--ai-depth", type=int, default=1, help="Max depth to use AI features")
    parser.add_argument("--ai-timeout", type=int, default=60, help="Timeout for AI agent actions")
    parser.add_argument("--strict", action="store_true", default=True, help="Enable strict element filtering")
    parser.add_argument("--no-strict", action="store_false", dest="strict", help="Disable strict element filtering")
    parser.add_argument("--dynamic", action="store_true", help="Enable dynamic crawl (allows crossing domains)")
    parser.add_argument("--exclude", nargs='*', help="List of URL paths to exclude")
    parser.add_argument("--camoufox", action="store_true", help="Use Camoufox stealth browser (default: False)")
    parser.add_argument("--max-interactions", type=int, default=8, help="Maximum interactions per page")

    args = parser.parse_args()

    # Get URLs from CLI args or .env
    target_urls = args.urls or ([os.getenv('TARGET_URL')] if os.getenv('TARGET_URL') else [])
    
    if not target_urls:
        print("ERROR: No URLs provided. Please provide one or more URLs as arguments or set TARGET_URL in .env file")
        print("Usage: python main.py <url1> <url2> ... [--use-ai] [--strict] [--dynamic]")
        return

    async def run_crawler_for_url(url):
        print(f"\n{'='*60}")
        print(f"Starting QA Garden Crawler for {url}")
        print(f"Mode: {'AI-Enhanced' if args.use_ai else 'Standard Fast'} | Strict Filtering: {args.strict} | Camoufox: {args.camoufox}")
        print(f"{'='*60}\n")

        # Create Configuration
        auth_creds = None
        email = os.getenv('LOGIN_EMAIL')
        password = os.getenv('LOGIN_PASSWORD')
        if email and password:
            auth_creds = {"email": email, "password": password}

        config = CrawlerConfig(
            url=url,
            max_pages=args.max_pages,
            max_depth=args.depth,
            headless=args.headless,
            use_ai=args.use_ai,
            ai_max_depth=args.ai_depth,
            strict_element_filtering=args.strict,
            dynamic_crawl=args.dynamic,
            exclude_paths=args.exclude if args.exclude else [],
            use_camoufox=args.camoufox,
            auth_creds=auth_creds,
            ai_timeout_sec=args.ai_timeout,
            max_interactions_per_page=args.max_interactions
        )

        # Initialize New Crawler
        crawler = QAGardenCrawler(config)

        print(f"Crawler started for {url}...")
        async for event in crawler.run():
            e_type = event.get("event")
            if e_type == "progress":
                print(f"[{event.get('depth', 0)}] Processing: {event.get('url')}")
            elif e_type == "pages_discovered":
                print(f"   -> Discovered {event.get('count')} links")
            elif e_type == "log":
                print(f"   -> {event.get('message')}")
            elif e_type == "completed":
                print(f"\nSUCCESS: {event.get('coverage_metric')}")
                if event.get("path"):
                    print(f"Output saved to: {event.get('path')}")

    async def run_all():
        for url in target_urls:
            try:
                await run_crawler_for_url(url)
            except Exception as e:
                print(f"\nError crawling {url}: {e}")
                import traceback
                traceback.print_exc()

    try:
        asyncio.run(run_all())
    except KeyboardInterrupt:
        print("\nCrawl stopped by user.")

if __name__ == "__main__":
    main()
