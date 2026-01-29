import asyncio
from playwright.async_api import async_playwright

async def debug_sklum():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False) # Headless False to see it
        context = await browser.new_context(
             user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
             viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        url = "https://www.sklum.com/es/633-comprar-sofas"
        print(f"Go to {url}")
        await page.goto(url)
        try:
            await page.click("#onetrust-accept-btn-handler", timeout=3000)
        except: pass
        
        await asyncio.sleep(3)
        
        # Check initial products
        initial_count = await page.locator(".c-product-card").count()
        print(f"Page 1 Count: {initial_count}")
        await page.screenshot(path="sklum_page1.png")
        
        # Try Next Button
        selectors = ['.js-next-page', 'a.next', '[rel="next"]']
        found = False
        for s in selectors:
            if await page.locator(s).count() > 0:
                print(f"Found Next Button: {s}")
                try:
                    await page.locator(s).first.scroll_into_view_if_needed()
                    await page.locator(s).first.click()
                    print("Clicked!")
                    found = True
                    break
                except Exception as e:
                    print(f"Error clicking {s}: {e}")
        
        if not found:
            print("❌ Next button NOT found via common selectors.")
            # Dump HTML to check
            with open("sklum_debug_page1.html", "w", encoding="utf-8") as f:
                f.write(await page.content())
        else:
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(5)
            new_count = await page.locator(".c-product-card").count()
            print(f"Page 2 Count (Accumulated/New): {new_count}")
            await page.screenshot(path="sklum_page2.png")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_sklum())
