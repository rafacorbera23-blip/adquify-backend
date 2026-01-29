
import asyncio
from playwright.async_api import async_playwright
import json
from pathlib import Path

async def debug_login():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False) # Ver navegador
        page = await browser.new_page()
        
        try:
            print("Navegando a login...")
            await page.goto("https://www.distrigalcatalogos.com/login/?redirect_to=https%3A%2F%2Fwww.distrigalcatalogos.com%2F", timeout=60000)
            await asyncio.sleep(5)
            
            print("Tomando screenshot inicial...")
            await page.screenshot(path="distrigal_login_page.png")
            
            # Imprimir HTML del formulario si existe
            form = await page.content()
            if "user_login" in form:
                print("Selector #user_login debería funcionar (texto encontrado en HTML)")
            else:
                print("⚠️ Texto 'user_login' NO encontrado en HTML")
                
            print("Intentando llenar credenciales...")
            await page.fill("#user_login", "blanca")
            await page.fill("#user_pass", "AlmacenBlanca30")
            await page.click("#wp-submit")
            
            print("Esperando navegación...")
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(5)
            
            print("Tomando screenshot final...")
            await page.screenshot(path="distrigal_after_login.png")
            
            if "tienda" in page.url or "mi-cuenta" in page.url:
                print("✅ LOGIN EXITOSO")
            else:
                print(f"❓ Estado incierto. URL actual: {page.url}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            await page.screenshot(path="distrigal_error.png")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_login())
