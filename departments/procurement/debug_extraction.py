
import asyncio
from playwright.async_api import async_playwright
import json
import re

def clean_price(text):
    if not text: return "0.0"
    return text.strip()

async def debug_extraction():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()
        
        print("\n=== DEBUG DISTRIGAL ===")
        try:
            # Login
            await page.goto("https://www.distrigalcatalogos.com/login/", timeout=60000)
            await page.fill("#user_login", "blanca")
            await page.fill("#user_pass", "AlmacenBlanca30")
            await page.click("#wp-submit")
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(3)
            
            # Ir a tienda
            print(f"Navegando a tienda: https://www.distrigalcatalogos.com/tienda/")
            await page.goto("https://www.distrigalcatalogos.com/tienda/", timeout=60000)
            await asyncio.sleep(5)
            
            await page.screenshot(path="debug_distrigal_shop.png")
            
            # Analizar items
            products = await page.query_selector_all(".product")
            print(f"Productos encontrados con selector '.product': {len(products)}")
            
            if len(products) > 0:
                p = products[0]
                print("--- Primer Producto ---")
                print("HTML:", await p.inner_html())
                
                title = await p.query_selector(".woocommerce-loop-product__title")
                print("Título:", await title.inner_text() if title else "NO ENCONTRADO")
                
                price = await p.query_selector(".price")
                print("Precio:", await price.inner_text() if price else "NO ENCONTRADO")
            else:
                # Si no hay .product, volcar todo el HTML para ver qué hay
                with open("distrigal_body.html", "w", encoding="utf-8") as f:
                    f.write(await page.content())
                print("Guardado HTML en distrigal_body.html")
                
        except Exception as e:
            print(f"Error Distrigal: {e}")

        print("\n=== DEBUG CASA THAI ===")
        try:
            # Login
            await page.goto("https://casathai.es/es/acceso?back=my-account", timeout=60000)
            
            # Cookies check
            if await page.query_selector("#onetrust-accept-btn-handler"):
                await page.click("#onetrust-accept-btn-handler")
            
            await page.fill("input[name='email']", "rafael@gpacontract.com")
            await page.fill("input[name='password']", "catalogo")
            await page.click("#submit-login")
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(3)
            
            print("Navegando a muebles: https://casathai.es/es/3-muebles")
            await page.goto("https://casathai.es/es/3-muebles", timeout=60000)
            await asyncio.sleep(5)
            
            await page.screenshot(path="debug_casathai_shop.png")
            
            products = await page.query_selector_all(".product-miniature")
            print(f"Productos encontrados con selector '.product-miniature': {len(products)}")
            
            if len(products) > 0:
                p = products[0]
                print("--- Primer Producto ---")
                
                title = await p.query_selector(".product-title")
                print("Título:", await title.inner_text() if title else "NO ENCONTRADO")
                
                price = await p.query_selector(".price")
                print("Precio:", await price.inner_text() if price else "NO ENCONTRADO")
                
        except Exception as e:
            print(f"Error Casa Thai: {e}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_extraction())
