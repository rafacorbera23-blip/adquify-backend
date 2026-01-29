from abc import ABC, abstractmethod
from typing import List, Dict, Any
from .browser_engine import BrowserEngine

class BaseHarvester(ABC):
    def __init__(self, supplier_code: str):
        self.supplier_code = supplier_code
        self.browser_engine = BrowserEngine()
        self.results: List[Dict[str, Any]] = []

    def start_session(self, headless: bool = False):
        """Starts the browser session"""
        self.browser_engine.start(headless=headless)

    def close_session(self):
        """Closes the browser session"""
        self.browser_engine.stop()

    @abstractmethod
    def login(self):
        """Implement login logic here"""
        pass

    @abstractmethod
    def extract_products(self):
        """Implement product extraction logic here"""
        pass

    def save_results(self):
        """Logic to save results to DB (Placeholder implementation)"""
        print(f"[{self.supplier_code}] Saving {len(self.results)} products to Database...")
        # In the next step, we will connect this to core/database.py
