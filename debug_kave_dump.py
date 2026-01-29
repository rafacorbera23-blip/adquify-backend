
import asyncio
from playwright.async_api import async_playwright

async def dump_kave():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
        page = await browser.new_page(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        )
        
        try:
            print("Navegando a Kave Home (Sofas)...")
            await page.goto("https://www.kavehome.com/es/es/c/sofas", timeout=60000)
            await asyncio.sleep(5)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            
            html = await page.content()
            with open("kave_dump.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("HTML guardado en kave_dump.html")
            
        except Exception as e:
            print(f"Error: {e}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(dump_kave())
