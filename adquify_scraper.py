import time
import random
import pandas as pd
from playwright.sync_api import sync_playwright
import requests

class AdquifyHarvester:
    def __init__(self):
        self.results = []
        # User Agents rotatorios para parecer humanos distintos
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        ]

    def random_sleep(self, min_s=2, max_s=5):
        time.sleep(random.uniform(min_s, max_s))

    def scrape_distrigal(self, page):
        print("🕵️ Iniciando Infiltración en Distrigal...")
        
        # 1. LOGIN
        page.goto("https://www.distrigalcatalogos.com/login/")
        self.random_sleep()
        
        # Rellenar credenciales (Inyectadas con seguridad)
        print("🔑 Autenticando...")
        page.fill("input[name='log']", "blanca")  # Selector asumiendo name='log' (común en WP)
        page.fill("input[name='pwd']", "AlmacenBlanca30")
        page.click("input[type='submit']") # O el selector del botón de entrar
        
        page.wait_for_load_state('networkidle')
        
        if "login" in page.url:
            print("❌ Fallo en Login Distrigal. Revisar selectores.")
            return

        print("✅ Login Exitoso. Extrayendo catálogo...")
        
        # 2. NAVEGACIÓN (Ejemplo: ir a una categoría maestra)
        # Aquí Antigravity debe poner la URL del listado de productos post-login
        target_url = "https://www.distrigalcatalogos.com/tienda/" # SUPOSICIÓN - AJUSTAR
        page.goto(target_url)
        
        # 3. EXTRACCIÓN (Iterar productos)
        products = page.query_selector_all(".product") # Selector genérico de WooCommerce
        
        for p in products:
            try:
                name = p.query_selector("h2").inner_text()
                price = p.query_selector(".price").inner_text()
                # Limpiar precio y aplicar multiplicador ADQUIFY
                clean_price = float(price.replace('€','').replace(',','.'))
                final_price = clean_price * 1.56 # Tu margen de importación
                
                self.results.append({
                    'Proveedor': 'Distrigal',
                    'Nombre': name,
                    'PVP_Origen': clean_price,
                    'PVP_Adquify': round(final_price, 2),
                    'Origen': 'Privado'
                })
            except:
                pass

    def scrape_public_site(self, page, url, provider_name, selectors):
        print(f"🌍 Analizando {provider_name} ({url})...")
        page.goto(url)
        
        # Manejo de Cookies (Aceptar todo para quitar el popup)
        try:
            page.click("text=Aceptar todas", timeout=3000) # Intento genérico
        except:
            pass

        # SCROLL INFINITO (Truco para cargar productos lazy-load)
        for _ in range(3):
            page.keyboard.press("End")
            self.random_sleep(1, 2)

        # EXTRACCIÓN
        items = page.query_selector_all(selectors['product_card'])
        print(f"📦 Detectados {len(items)} productos potenciales en home...")

        for item in items[:10]: # Limite de prueba
            try:
                name = item.query_selector(selectors['title']).inner_text()
                price_text = item.query_selector(selectors['price']).inner_text()
                
                self.results.append({
                    'Proveedor': provider_name,
                    'Nombre': name,
                    'Precio_Texto': price_text, # Necesita limpieza posterior
                    'Origen': 'Público'
                })
            except Exception as e:
                continue

    def run(self):
        with sync_playwright() as p:
            # Lanzar navegador (headless=False para ver qué hace al depurar)
            browser = p.chromium.launch(headless=False) 
            context = browser.new_context(user_agent=random.choice(self.user_agents))
            page = context.new_page()

            # --- EJECUCIÓN SECUENCIAL ---
            
            # 1. DISTRIGAL (Privado)
            try:
                self.scrape_distrigal(page)
            except Exception as e:
                print(f"⚠️ Error en Distrigal: {e}")

            # 2. SKLUM (Público - Difícil)
            # Selectores aproximados (Antigravity debe verificar con F12 actual)
            sklum_selectors = {
                'product_card': 'article.product-miniature',
                'title': 'h3.product-title',
                'price': 'span.price'
            }
            self.scrape_public_site(page, "https://www.sklum.com/es/", "Sklum", sklum_selectors)

            # 3. KAVE HOME (Público)
            kave_selectors = {
                'product_card': 'div.product-card', # Verificar selector
                'title': '[data-testid="product-card-title"]',
                'price': '[data-testid="product-card-price"]'
            }
            self.scrape_public_site(page, "https://kavehome.com/es/es", "Kave Home", kave_selectors)

            browser.close()
            
            # GUARDAR
            df = pd.DataFrame(self.results)
            df.to_csv("Adquify_Master_Scrape.csv", index=False)
            print("💾 Datos guardados en Adquify_Master_Scrape.csv")

if __name__ == "__main__":
    bot = AdquifyHarvester()
    bot.run()
