import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from config.urls import PAGE_1_CDBD_URL
from playwright.sync_api import expect
import re

def test_TC_Login_Flow_1(page):
    page.goto(PAGE_1_CDBD_URL)
    page.locator('#login-email').fill('test@example.com')
    page.locator('button.login-button').click()
    expect(page.locator('h2.welcome-text')).to_be_visible(timeout=10000)

def test_TC_Navigation_Sign_Up_2(page):
    page.goto(PAGE_1_CDBD_URL)
    page.locator('a').click()
    expect(page).to_have_url(re.compile(r"/signup"))

def test_TC_Navigation_Forgot_Password_3(page):
    page.goto(PAGE_1_CDBD_URL)
    page.locator('a.forgot-link').click()
    expect(page).to_have_url(re.compile(r"/forgot-password"))