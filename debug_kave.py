
import asyncio
from playwright.async_api import async_playwright
import random

async def scrape_kave_debug():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled', 
                '--no-sandbox',
                '--disable-infobars',
                '--exclude-switches=enable-automation'
            ]
        )
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            locale='es-ES'
        )
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = await context.new_page()
        print("🌍 Navegando a Kave Home...")
        try:
            await page.goto("https://www.kavehome.com/es/es", timeout=60000)
            await asyncio.sleep(5)
            
            title = await page.title()
            print(f"TITLE: {title}")
            
            # Screenshot para ver si hay bloqueo
            await page.screenshot(path="kave_debug.png")
            
            # Intentar ver categorías
            cats = await page.query_selector_all('nav a, header a')
            print(f"Links encontrados en header: {len(cats)}")
            
            # Navegar a sofas
            print("Navegando a sofas...")
            await page.goto("https://www.kavehome.com/es/es/c/sofas", timeout=60000)
            await asyncio.sleep(5)
            await page.screenshot(path="kave_sofas_debug.png")
            
            # Ver productos
            products = await page.evaluate("""
                () => {
                    return document.querySelectorAll('article, [class*="product"]').length;
                }
            """)
            print(f"Productos detectados (JS): {products}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            await page.screenshot(path="kave_error.png")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_kave_debug())
