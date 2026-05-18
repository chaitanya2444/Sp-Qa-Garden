
import asyncio
from playwright.async_api import async_playwright
import os

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print(f"Navigating to login page...")
        await page.goto("https://www.snappod.ai/login", wait_until="networkidle")
        await asyncio.sleep(5) # Wait for eventual redirects/hydration
        
        print(f"Current URL: {page.url}")
        
        frames = page.frames
        print(f"Total Frames: {len(frames)}")
        for i, frame in enumerate(frames):
            print(f"Frame {i}: {frame.name} | {frame.url}")
            content = (await frame.content()).lower()
            if "email" in content or "password" in content or "login" in content:
                print(f"  --> Frame {i} contains auth keywords!")
                # Look for inputs
                inputs = await frame.query_selector_all("input")
                print(f"  --> Found {len(inputs)} inputs in Frame {i}")
                for inp in inputs:
                    p_type = await inp.get_attribute("type")
                    p_id = await inp.get_attribute("id")
                    p_name = await inp.get_attribute("name")
                    print(f"    - Input: type={p_type}, id={p_id}, name={p_name}")

        await page.screenshot(path="final_diag_state.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
