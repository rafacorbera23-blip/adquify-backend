import asyncio
from playwright.async_api import async_playwright, Page
import random

# User-Agent rotation list (simplified for demo)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"
]

class UniversalLoader:
    """
    Robust webpage loader designed to bypass basic bot detection and handle dynamic content.
    Follows 'browser-automation' skill best practices:
    - Stealth (User-Agent rotation, hidden webdriver flags)
    - Auto-Wait (mostly implicit in Playwright, but we add smart logic)
    """
    
    def __init__(self, headless=True):
        self.headless = headless

    async def fetch_page_content(self, url: str) -> str:
        """
        Loads a URL and returns the full HTML content after dynamic rendering.
        """
        print(f"🌍 [Loader] Navigating to: {url}")
        
        async with async_playwright() as p:
            # Launch browser with stealth-like args
            browser = await p.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"]
            )
            
            # Create context with randomized user agent
            context = await browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1920, "height": 1080}
            )
            
            # Add init script to mask webdriver property
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

            page = await context.new_page()
            
            try:
                # 1. Navigation with robust timeout
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                
                # 2. Smart Wait: Wait for network to be idle-ish or a key element
                # Using a safe fallback wait if 'networkidle' is flaky
                try:
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except:
                    print("⚠️ [Loader] Network idle timeout, proceeding anyway...")

                # 3. auto-scroll to trigger lazy loading
                await self._auto_scroll(page)
                
                # 4. Get Content
                content = await page.content()
                print(f"✅ [Loader] Successfully loaded {len(content)} bytes.")
                return content
                
            except Exception as e:
                print(f"❌ [Loader] Error fetching {url}: {e}")
                return ""
            finally:
                await browser.close()

    async def _auto_scroll(self, page: Page):
        """
        Gentle auto-scroll to trigger lazy-loaded images/products.
        """
        await page.evaluate("""
            async () => {
                await new Promise((resolve) => {
                    let totalHeight = 0;
                    let distance = 100;
                    let timer = setInterval(() => {
                        let scrollHeight = document.body.scrollHeight;
                        window.scrollBy(0, distance);
                        totalHeight += distance;

                        if(totalHeight >= scrollHeight - window.innerHeight || totalHeight > 5000){
                            clearInterval(timer);
                            resolve();
                        }
                    }, 100);
                });
            }
        """)
        # Brief pause after scroll to let items render
        await page.wait_for_timeout(2000)

if __name__ == "__main__":
    # Test run
    loader = UniversalLoader(headless=False)
    html = asyncio.run(loader.fetch_page_content("https://example.com"))
    print(html[:500])
