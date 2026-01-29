from playwright.sync_api import sync_playwright, Page, BrowserContext
import random
import time
from pathlib import Path

class BrowserEngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BrowserEngine, cls).__new__(cls)
            cls._instance.playwright = None
            cls._instance.browser = None
            cls._instance.context = None
            cls._instance.page = None
        return cls._instance

    def start(self, headless: bool = False):
        if not self.playwright:
            self.playwright = sync_playwright().start()
        
        if not self.browser:
            self.browser = self.playwright.chromium.launch(
                headless=headless,
                args=["--disable-blink-features=AutomationControlled"]
            )
            
            # TODO: Load storage_state.json if exists for persistence
            
            self.context = self.browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            
            self.page = self.context.new_page()

    def get_page(self) -> Page:
        if not self.page:
            raise Exception("Browser not started. Call start() first.")
        return self.page

    def stop(self):
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        
        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None

    def random_sleep(self, min_s: float = 1.0, max_s: float = 3.0):
        time.sleep(random.uniform(min_s, max_s))
