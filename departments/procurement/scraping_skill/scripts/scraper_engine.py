import asyncio
import random
import json
import logging
import os
from typing import List
import logging
import os
from typing import List
from playwright.async_api import async_playwright, Page, BrowserContext

# Config
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
MAX_CONCURRENT_WORKERS = 5
PAGE_TIMEOUT_MS = 60000

class MassScraper:
    def __init__(self, urls: List[str]):
        self.urls = urls
        self.results = []
        self.failed_urls = []
        self.queue = asyncio.Queue()

    async def _setup_page(self, context: BrowserContext) -> Page:
        page = await context.new_page()
        # Manual Stealth Injection (Robust fallback)
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'languages', { get: () => ['es-ES', 'es', 'en-US', 'en'] });
            window.chrome = { runtime: {} };
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
            );
        """)
        return page

    async def worker(self, name: str, browser):
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='es-ES'
        )
        
        while True:
            try:
                url = self.queue.get_nowait()
            except asyncio.QueueEmpty:
                break

            try:
                logger.info(f"[{name}] Extrayendo: {url}")
                page = await self._setup_page(context)
                
                # Cookie Consent Try (Generic JS)
                try:
                    await page.goto(url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
                    # Try clicking generic cookie buttons
                    await page.evaluate("""() => {
                        const buttons = document.querySelectorAll("button, a");
                        for (let btn of buttons) {
                            if (btn.innerText.toLowerCase().includes("aceptar") || btn.innerText.toLowerCase().includes("accept")) {
                                btn.click();
                            }
                        }
                    }""")
                    await asyncio.sleep(2)
                except Exception as e:
                    logger.warning(f"Nav warning: {e}")

                content = await page.content()
                self.results.append({
                    "url": url,
                    "html_content": content,
                    "status": "success"
                })
                logger.info(f"[{name}] Éxito: {url}")
                await page.close()

            except Exception as e:
                logger.error(f"[{name}] Fallo: {e}")
                self.failed_urls.append({"url": url, "reason": str(e)})
            finally:
                self.queue.task_done()

        await context.close()

    async def run(self):
        for url in self.urls:
            self.queue.put_nowait(url)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            workers = []
            for i in range(MAX_CONCURRENT_WORKERS):
                task = asyncio.create_task(self.worker(f"Worker-{i+1}", browser))
                workers.append(task)

            await asyncio.gather(*workers)
            await browser.close()

        return self.results

if __name__ == "__main__":
    # PRODUCTION ENTRY POINT: FULL CATALOG SWEEP
    # ==========================================
    # Categories to sweep for Sklum/Kave (EXPANDED)
    categories = [
        # SKLUM Categories
        "https://www.sklum.com/es/sillas-comedor", 
        "https://www.sklum.com/es/mesas-comedor",
        "https://www.sklum.com/es/sofas",
        "https://www.sklum.com/es/iluminacion",
        "https://www.sklum.com/es/decoracion",
        "https://www.sklum.com/es/exterior",
        "https://www.sklum.com/es/dormitorio",
        "https://www.sklum.com/es/oficina",
        # KAVE Categories
        "https://kavehome.com/es/es/sillas-comedor",
        "https://kavehome.com/es/es/mesas-comedor",
        "https://kavehome.com/es/es/sofas",
        "https://kavehome.com/es/es/iluminacion",
        "https://kavehome.com/es/es/decoracion",
        # CASA TAI
        "https://www.casatai.com/hosteleria"
    ]
    
    # Generate pagination URLs: 50 pages per category = EXHAUSTIVE SWEEP
    MAX_PAGES = 50  # Sklum has ~30-40 pages per category, this ensures we get EVERYTHING
    full_target_list = []
    
    for base_url in categories:
        full_target_list.append(base_url)
        if "casatai" in base_url: continue
        
        for i in range(2, MAX_PAGES + 1):
            if "sklum" in base_url: 
                full_target_list.append(f"{base_url}?page={i}")
            if "kave" in base_url: 
                full_target_list.append(f"{base_url}?page={i}")

    print(f"🎯 Total URLs to scrape: {len(full_target_list)}")
    
    scraper = MassScraper(full_target_list)
    data = asyncio.run(scraper.run())
    
    with open("raw_scraping_results.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Scraped {len(data)} pages.")
