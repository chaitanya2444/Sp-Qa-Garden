import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from config.urls import PAGE_2_F871_URL
from playwright.sync_api import expect
import re

def test_TC_Authentication_01(page):
    page.goto(PAGE_2_F871_URL)
    page.locator('input.ant-input.ant-input-outlined').fill("John")
    page.locator('input.ant-input.ant-input-outlined').nth(1).fill("Doe")
    page.locator('input.ant-input.ant-input-outlined').nth(2).fill("john.doe@example.com")
    page.locator('input.ant-input').nth(0).fill("P@sswOrd123")
    page.locator('input.ant-input').nth(1).fill("P@sswOrd123")
    page.locator('button').click()

def test_TC_Navigation_01(page):
    page.goto(PAGE_2_F871_URL)
    page.locator('a').click()
    expect(page).to_have_url(re.compile(r"\/login"))