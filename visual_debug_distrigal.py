
import asyncio
from playwright.async_api import async_playwright
import json

async def capture_distrigal():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        print("Navegando a Login Distrigal...")
        await page.goto("https://www.distrigalcatalogos.com/login/")
        await asyncio.sleep(2)
        
        try:
            # Ultimate Member Selectors
            await page.fill(".um-field-username input", "blanca")
            await page.fill(".um-field-user_password input", "AlmacenBlanca30")
            await page.click("#um-submit-btn")
            print("Click submit done.")
        except Exception as e:
            print(f"Error llenando form: {e}")
            
        await asyncio.sleep(8)
        print(f"URL actual: {page.url}")
        
        # Navigate to shop
        await page.goto("https://www.distrigalcatalogos.com/tienda/")
        await asyncio.sleep(5)
        
        # Screenshot
        await page.screenshot(path="distrigal_debug.png")
        
        # Save HTML
        content = await page.content()
        with open("distrigal_shop.html", "w", encoding="utf-8") as f:
            f.write(content)
            
        print("Guardado distrigal_debug.png y distrigal_shop.html")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture_distrigal())
