
import asyncio
from playwright.async_api import async_playwright

async def capture_distrigal_shop():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=100)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()
        
        print("1. Navegando a Login...")
        await page.goto("https://www.distrigalcatalogos.com/login/")
        await asyncio.sleep(3)
        
        print("2. Llenando credenciales...")
        await page.fill(".um-field-username input", "blanca")
        await page.fill(".um-field-user_password input", "AlmacenBlanca30")
        await page.click("#um-submit-btn")
        
        print("3. Esperando redirección...")
        await asyncio.sleep(8)
        print(f"   URL: {page.url}")
        
        print("4. Navegando a tienda...")
        await page.goto("https://www.distrigalcatalogos.com/tienda/")
        await asyncio.sleep(5)
        
        # Scroll
        for _ in range(5):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await asyncio.sleep(1)
        
        print("5. Capturando HTML...")
        content = await page.content()
        with open("distrigal_tienda_final.html", "w", encoding="utf-8") as f:
            f.write(content)
        
        await page.screenshot(path="distrigal_tienda_final.png", full_page=True)
        print("✅ Guardado: distrigal_tienda_final.html y .png")
        
        # Buscar productos
        products = await page.query_selector_all(".product")
        print(f"Productos con .product: {len(products)}")
        
        products2 = await page.query_selector_all("li.product")
        print(f"Productos con li.product: {len(products2)}")
        
        products3 = await page.query_selector_all("[class*='product']")
        print(f"Elementos con 'product' en clase: {len(products3)}")
        
        # Mostrar clases de elementos encontrados
        if products3:
            for i, p in enumerate(products3[:10]):
                cls = await p.get_attribute("class")
                print(f"   {i}: {cls}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture_distrigal_shop())
