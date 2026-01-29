
import asyncio
from playwright.async_api import async_playwright
import sys

async def fix_distrigal():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        try:
            print("Navegando a landing de login...")
            await page.goto("https://www.distrigalcatalogos.com/login/", timeout=60000)
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(2)
            
            print("Buscando inputs...")
            # Try multiple selectors
            selectors = ["#user_login", "input[name='log']", "#username", "input[type='text']"]
            found_sel = None
            for sel in selectors:
                if await page.query_selector(sel):
                    print(f"✓ Encontrado selector: {sel}")
                    found_sel = sel
                    break
            
            if found_sel:
                print(f"Llenando usuario en {found_sel}...")
                await page.fill(found_sel, "blanca")
                await page.fill("#user_pass" if await page.query_selector("#user_pass") else "input[name='pwd']", "AlmacenBlanca30")
                
                print("Click login...")
                await page.click("#wp-submit" if await page.query_selector("#wp-submit") else "input[type='submit']")
                
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(3)
                
                print(f"URL actual: {page.url}")
                if "tienda" in page.url or "distrigalcatalogos.com" in page.url:
                    print("✅ Login parece exitoso, navegando a tienda...")
                    await page.goto("https://www.distrigalcatalogos.com/tienda/")
                    await asyncio.sleep(3)
                    
                    products = await page.query_selector_all(".product")
                    print(f"Productos encontrados: {len(products)}")
            else:
                print("❌ No se encontró ningún input de login.")
                print(await page.content())
                
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(fix_distrigal())
