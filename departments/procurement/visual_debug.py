
import asyncio
from playwright.async_api import async_playwright

async def save_htmls():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Distrigal
        try:
            print("Login Distrigal...")
            await page.goto("https://www.distrigalcatalogos.com/login/")
            await page.fill("#user_login", "blanca", force=True)
            await page.fill("#user_pass", "AlmacenBlanca30", force=True)
            await page.click("#wp-submit", force=True)
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(5)
            
            print("Navegando a Tienda...")
            await page.goto("https://www.distrigalcatalogos.com/tienda/")
            await asyncio.sleep(5)
            
            content = await page.content()
            with open("distrigal_shop.html", "w", encoding="utf-8") as f:
                f.write(content)
            print("Saved distrigal_shop.html")
            await page.screenshot(path="distrigal_shop_final.png")
            
        except Exception as e:
            print(f"Error Distrigal: {e}")
            
        # Casa Thai
        try:
            print("Login Casa Thai...")
            await page.goto("https://casathai.es/es/acceso?back=my-account")
            # Popups
            try:
                await page.click("#onetrust-accept-btn-handler", timeout=2000)
            except: pass
            
            await page.fill("input[name='email']", "rafael@gpacontract.com", force=True)
            await page.fill("input[name='password']", "catalogo", force=True)
            await page.click("#submit-login", force=True)
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(5)
            
            print("Navegando a Muebles...")
            await page.goto("https://casathai.es/es/3-muebles")
            await asyncio.sleep(5)
            
            content = await page.content()
            with open("casathai_shop.html", "w", encoding="utf-8") as f:
                f.write(content)
            print("Saved casathai_shop.html")
            await page.screenshot(path="casathai_shop_final.png")
            
        except Exception as e:
            print(f"Error Casa Thai: {e}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(save_htmls())
