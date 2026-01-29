"""
Adquify Engine - Web Scraper con Login (Playwright)
=====================================================
Scraper genérico para sitios que requieren autenticación.
"""

import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
import hashlib

# Paths
ENGINE_ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = ENGINE_ROOT / "config" / "suppliers_credentials.json"
DATA_RAW = ENGINE_ROOT / "data" / "raw"

def load_supplier_config(supplier_code: str) -> Optional[Dict]:
    """Carga configuración de un proveedor"""
    if not CONFIG_PATH.exists():
        print(f"❌ No se encontró archivo de configuración: {CONFIG_PATH}")
        return None
    
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    return config.get('suppliers', {}).get(supplier_code)

def generate_sku(supplier_code: str, name: str, url: str, index: int) -> str:
    """Genera SKU único"""
    prefix = supplier_code[:2].upper()
    hash_part = hashlib.md5(f"{name}{url}".encode()).hexdigest()[:6].upper()
    return f"ADQ-{prefix}-{hash_part}-{index:04d}"

async def scrape_with_login(supplier_code: str, max_pages: int = 5, dry_run: bool = True):
    """
    Ejecuta scraping con login usando Playwright.
    
    Args:
        supplier_code: Código del proveedor (KAVE, SKLUM, etc.)
        max_pages: Número máximo de páginas a scrapear
        dry_run: Si es True, no guarda datos
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("❌ Playwright no instalado. Ejecuta: pip install playwright && playwright install")
        return None
    
    config = load_supplier_config(supplier_code)
    if not config:
        print(f"❌ No hay configuración para {supplier_code}")
        return None
    
    creds = config.get('credentials', {})
    if not creds.get('email') or not creds.get('password'):
        print(f"⚠️ Credenciales vacías para {supplier_code}")
        print(f"   Configura en: {CONFIG_PATH}")
        return None
    
    selectors = config.get('selectors', {})
    rate_limit = config.get('rateLimit', {})
    delay = rate_limit.get('delayBetweenPages', 2000) / 1000  # Convertir a segundos
    
    print("="*60)
    print(f"🤖 ADQUIFY ENGINE - Web Scraper {config['name']}")
    print("="*60)
    
    products = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # headless=False para debug
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # 1. Login
            print(f"\n🔐 Iniciando sesión en {config['loginUrl']}...")
            await page.goto(config['loginUrl'])
            await page.wait_for_load_state('networkidle')
            
            # Rellenar formulario
            await page.fill(selectors['emailInput'], creds['email'])
            await page.fill(selectors['passwordInput'], creds['password'])
            await page.click(selectors['submitButton'])
            
            # Esperar navegación post-login
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)
            
            print("✅ Login completado")
            
            # 2. Navegar al catálogo
            print(f"\n📂 Navegando al catálogo: {config['catalogUrl']}")
            await page.goto(config['catalogUrl'])
            await page.wait_for_load_state('networkidle')
            
            # 3. Extraer productos
            print(f"\n🔍 Extrayendo productos (máx {max_pages} páginas)...")
            
            for page_num in range(max_pages):
                print(f"   Página {page_num + 1}...")
                
                # Obtener productos de la página actual
                product_cards = await page.query_selector_all(selectors['productCard'])
                
                for idx, card in enumerate(product_cards):
                    try:
                        name_el = await card.query_selector(selectors['productName'])
                        price_el = await card.query_selector(selectors['productPrice'])
                        img_el = await card.query_selector(selectors['productImage'])
                        
                        name = await name_el.inner_text() if name_el else ''
                        price_text = await price_el.inner_text() if price_el else '0'
                        img_src = await img_el.get_attribute('src') if img_el else ''
                        
                        # Limpiar precio
                        price = 0.0
                        try:
                            price_clean = price_text.replace('€', '').replace(',', '.').strip()
                            price = float(price_clean)
                        except:
                            pass
                        
                        if name:
                            product = {
                                'sku_adquify': generate_sku(supplier_code, name, img_src, len(products)),
                                'sku_supplier': '',
                                'supplier_code': supplier_code,
                                'name_original': name.strip(),
                                'name_commercial': name.strip().title(),
                                'price_supplier': price,
                                'price_adquify': round(price * 1.25, 2),  # 25% margen default
                                'images': [img_src] if img_src else [],
                                'stock_available': True,
                                'source': 'web_scraping',
                                'created_at': datetime.utcnow().isoformat()
                            }
                            products.append(product)
                    except Exception as e:
                        continue
                
                # Intentar ir a la siguiente página
                try:
                    next_btn = await page.query_selector('.pagination-next, .next-page, [aria-label="Next"]')
                    if next_btn:
                        await next_btn.click()
                        await page.wait_for_load_state('networkidle')
                        await asyncio.sleep(delay)
                    else:
                        break
                except:
                    break
            
            print(f"\n✅ Extraídos {len(products)} productos")
            
        except Exception as e:
            print(f"❌ Error durante scraping: {e}")
        finally:
            await browser.close()
    
    # Guardar resultados
    if products and not dry_run:
        DATA_RAW.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = DATA_RAW / f"{supplier_code.lower()}_web_{timestamp}.json"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                'supplier': supplier_code,
                'source': 'web_scraping',
                'extracted_at': datetime.utcnow().isoformat(),
                'total_products': len(products),
                'products': products
            }, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Guardado en: {output_path}")
    
    return products

def run_web_scraper(supplier_code: str, max_pages: int = 5, dry_run: bool = True):
    """Wrapper síncrono para el scraper async"""
    return asyncio.run(scrape_with_login(supplier_code, max_pages, dry_run))

if __name__ == "__main__":
    import sys
    
    supplier = sys.argv[1] if len(sys.argv) > 1 else "KAVE"
    print(f"Ejecutando scraper para: {supplier}")
    run_web_scraper(supplier, max_pages=2, dry_run=True)
