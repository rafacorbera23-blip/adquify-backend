
import asyncio
from playwright.async_api import async_playwright

async def dump_sklum():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
        page = await browser.new_page(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        )
        
        try:
            print("Navegando a Sklum...")
            await page.goto("https://www.sklum.com/es/633-comprar-sofas", timeout=60000)
            await asyncio.sleep(5)
            
            # Scroll un poco
            await page.evaluate("window.scrollBy(0, 500)")
            await asyncio.sleep(2)
            
            html = await page.content()
            with open("sklum_dump.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("HTML guardado en sklum_dump.html")
            
            await page.screenshot(path="sklum_dump.png")
            
        except Exception as e:
            print(f"Error: {e}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(dump_sklum())
