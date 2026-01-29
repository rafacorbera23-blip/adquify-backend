from abc import ABC, abstractmethod
from typing import List, Dict
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup

# Standard Output Format - "The Universal Language"
class ScrapedProduct(BaseModel):
    name: str
    price: float
    sku_supplier: str
    description: str
    images: List[str]
    specs: Dict[str, str] # e.g. {"Material": "Wood", "Dimensions": "50x50"}

class BaseScraperAgent(ABC):
    """
    The 'Communicator Agent'.
    Mission: Read any website and translate it into Adquify's internal language.
    """
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    def fetch_page(self, url: str) -> BeautifulSoup:
        """Reads a page using Selenium (The Eyes v2)"""
        print(f"👀 Reading (Selenium): {url}")
        self.driver.get(url)
        # Wait for potential js load
        import time
        time.sleep(5) # Increased wait just in case
        self.driver.save_screenshot("debug_scraper_view.png") # Visual Debug
        print(f"📸 Screenshot saved: debug_scraper_view.png")
        return BeautifulSoup(self.driver.page_source, 'html.parser')

    def close(self):
        if self.driver:
            self.driver.quit()

    @abstractmethod
    def extract_products(self, soup: BeautifulSoup) -> List[ScrapedProduct]:
        """Translates the page (The Brain)"""
        pass

    @abstractmethod
    def navigate_next(self, soup: BeautifulSoup) -> str:
        """Finds more data (The Feet)"""
        pass
