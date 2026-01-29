"""
Adquify Engine - Scraper Completo V2 (Método Directo)
======================================================
Extrae TODOS los productos navegando el sitemap y scrapeando cards directamente.
"""

import json
import asyncio
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Set
import random

ENGINE_ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = ENGINE_ROOT / "config" / "suppliers_credentials.json"
DATA_RAW = ENGINE_ROOT / "data" / "raw"

def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"suppliers": {}}

def generate_sku(supplier_code: str, url: str, index: int) -> str:
    prefix = supplier_code[:2].upper()
    hash_part = hashlib.md5(url.encode()).hexdigest()[:8].upper()
    return f"ADQ-{prefix}-{hash_part}"

def clean_price(text: str) -> float:
    if not text:
        return 0.0
    cleaned = re.sub(r'[^\d,.]', '', text)
    if ',' in cleaned and '.' in cleaned:
        if cleaned.index('.') < cleaned.index(','):
            cleaned = cleaned.replace('.', '').replace(',', '.')
        else:
            cleaned = cleaned.replace(',', '')
    elif ',' in cleaned:
        cleaned = cleaned.replace(',', '.')
    try:
        return float(cleaned)
    except:
        return 0.0

async def human_delay(min_s=1, max_s=3):
    await asyncio.sleep(random.uniform(min_s, max_s))

async def scrape_kave_complete(page, status_callback: dict) -> List[Dict]:
    """Scraper de Kave usando JavaScript para extraer todos los productos visibles"""
    all_products = []
    seen_urls: Set[str] = set()
    
    categories = [
        ('Sofás', 'https://www.kavehome.com/es/es/c/sofas'),
        ('Sillas', 'https://www.kavehome.com/es/es/c/sillas'),
        ('Mesas', 'https://www.kavehome.com/es/es/c/mesas'),
        ('Mesas de Centro', 'https://www.kavehome.com/es/es/c/mesas-de-centro'),
        ('Mesas de Comedor', 'https://www.kavehome.com/es/es/c/mesas-de-comedor'),
        ('Almacenaje', 'https://www.kavehome.com/es/es/c/almacenaje'),
        ('Camas', 'https://www.kavehome.com/es/es/c/camas'),
        ('Mesitas de Noche', 'https://www.kavehome.com/es/es/c/mesitas-de-noche'),
        ('Cómodas', 'https://www.kavehome.com/es/es/c/comodas'),
        ('Muebles TV', 'https://www.kavehome.com/es/es/c/muebles-tv'),
        ('Escritorios', 'https://www.kavehome.com/es/es/c/escritorios'),
        ('Estanterías', 'https://www.kavehome.com/es/es/c/estanterias'),
        ('Aparadores', 'https://www.kavehome.com/es/es/c/aparadores'),
        ('Sillones', 'https://www.kavehome.com/es/es/c/sillones'),
        ('Taburetes', 'https://www.kavehome.com/es/es/c/taburetes'),
        ('Bancos', 'https://www.kavehome.com/es/es/c/bancos'),
        ('Pufs', 'https://www.kavehome.com/es/es/c/pufs'),
        ('Muebles Exterior', 'https://www.kavehome.com/es/es/c/muebles-de-jardin-y-terraza'),
        ('Sofás Exterior', 'https://www.kavehome.com/es/es/c/sofas-de-exterior'),
        ('Iluminación', 'https://www.kavehome.com/es/es/c/iluminacion'),
        ('Lámparas de Techo', 'https://www.kavehome.com/es/es/c/lamparas-de-techo'),
        ('Lámparas de Mesa', 'https://www.kavehome.com/es/es/c/lamparas-de-mesa'),
        ('Lámparas de Pie', 'https://www.kavehome.com/es/es/c/lamparas-de-pie'),
        ('Espejos', 'https://www.kavehome.com/es/es/c/espejos'),
        ('Cuadros', 'https://www.kavehome.com/es/es/c/cuadros'),
        ('Jarrones', 'https://www.kavehome.com/es/es/c/jarrones'),
        ('Alfombras', 'https://www.kavehome.com/es/es/c/alfombras'),
        ('Cojines', 'https://www.kavehome.com/es/es/c/cojines'),
        ('Mantas', 'https://www.kavehome.com/es/es/c/mantas'),
    ]
    
    try:
        status_callback['KAVE']['message'] = 'Aceptando cookies...'
        await page.goto('https://www.kavehome.com/es/es', timeout=60000)
        await asyncio.sleep(3)
        
        try:
            btn = await page.query_selector('#onetrust-accept-btn-handler')
            if btn:
                await btn.click()
                await asyncio.sleep(1)
        except:
            pass
        
        total_cats = len(categories)
        
        for idx, (cat_name, cat_url) in enumerate(categories):
            progress = int(((idx + 1) / total_cats) * 95)
            status_callback['KAVE']['message'] = f'[{idx+1}/{total_cats}] {cat_name}...'
            status_callback['KAVE']['progress'] = progress
            
            print(f"\n📂 [{idx+1}/{total_cats}] {cat_name}")
            
            try:
                await page.goto(cat_url, timeout=60000)
                await asyncio.sleep(3)
                
                # Scroll agresivo
                for _ in range(20):
                    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    await asyncio.sleep(0.8)
                
                # Extraer con JavaScript
                products_data = await page.evaluate("""
                    () => {
                        const products = [];
                        
                        // Buscar todos los links a productos
                        const links = document.querySelectorAll('a[href*="/es/p/"], a[href*="/p/"]');
                        const seenHrefs = new Set();
                        
                        links.forEach(link => {
                            const href = link.href;
                            if (seenHrefs.has(href)) return;
                            seenHrefs.add(href);
                            
                            // Buscar el contenedor del producto
                            let container = link.closest('article') || link.closest('[class*="product"]') || link.closest('[class*="tile"]') || link.parentElement?.parentElement;
                            
                            // Nombre
                            let name = '';
                            if (container) {
                                const nameEl = container.querySelector('h2, h3, [class*="name"], [class*="title"]');
                                name = nameEl ? nameEl.innerText.trim() : '';
                            }
                            if (!name) {
                                name = link.innerText.trim().split('\\n')[0];
                            }
                            
                            // Imagen
                            let imgSrc = '';
                            if (container) {
                                const img = container.querySelector('img');
                                if (img) {
                                    imgSrc = img.src || img.dataset.src || '';
                                }
                            }
                            
                            // Precio
                            let price = '';
                            if (container) {
                                const priceEl = container.querySelector('[class*="price"]');
                                if (priceEl) {
                                    price = priceEl.innerText.trim();
                                }
                            }
                            
                            if (name && name.length > 2) {
                                products.push({
                                    url: href,
                                    name: name.substring(0, 150),
                                    image: imgSrc,
                                    price: price
                                });
                            }
                        });
                        
                        return products;
                    }
                """)
                
                new_count = 0
                for p in products_data:
                    url = p.get('url', '')
                    if not url or url in seen_urls:
                        continue
                    
                    seen_urls.add(url)
                    new_count += 1
                    
                    price = clean_price(p.get('price', ''))
                    img = p.get('image', '')
                    if img.startswith('//'):
                        img = 'https:' + img
                    
                    all_products.append({
                        'sku_adquify': generate_sku('KAVE', url, len(all_products)),
                        'supplier_code': 'KAVE',
                        'name_original': p.get('name', ''),
                        'name_commercial': p.get('name', ''),
                        'category': cat_name,
                        'price_supplier': price,
                        'price_adquify': round(price * 1.30, 2) if price > 0 else 0,
                        'margin': 0.30,
                        'images': [img] if img else [],
                        'product_url': url,
                        'status': 'pending',
                        'source': 'web_scraping',
                        'created_at': datetime.utcnow().isoformat()
                    })
                
                print(f"   ✓ Nuevos: {new_count} | Total acumulado: {len(all_products)}")
                await human_delay(1, 2)
                
            except Exception as e:
                print(f"   ✗ Error: {e}")
                continue
        
        status_callback['KAVE']['message'] = f'✓ {len(all_products)} productos'
        status_callback['KAVE']['progress'] = 100
        
    except Exception as e:
        print(f"Error general: {e}")
    
    return all_products

async def scrape_sklum_complete(page, status_callback: dict) -> List[Dict]:
    """Scraper de Sklum"""
    all_products = []
    seen_urls: Set[str] = set()
    
    categories = [
        ('Sofás', 'https://www.sklum.com/es/sofas'),
        ('Sillas', 'https://www.sklum.com/es/sillas'),
        ('Sillas de Comedor', 'https://www.sklum.com/es/sillas-comedor'),
        ('Sillas de Oficina', 'https://www.sklum.com/es/sillas-oficina'),
        ('Mesas', 'https://www.sklum.com/es/mesas'),
        ('Mesas de Comedor', 'https://www.sklum.com/es/mesas-comedor'),
        ('Mesas de Centro', 'https://www.sklum.com/es/mesas-centro'),
        ('Escritorios', 'https://www.sklum.com/es/mesas-escritorio'),
        ('Almacenaje', 'https://www.sklum.com/es/almacenaje'),
        ('Estanterías', 'https://www.sklum.com/es/estanterias'),
        ('Cómodas', 'https://www.sklum.com/es/comodas-cajoneras'),
        ('Aparadores', 'https://www.sklum.com/es/aparadores'),
        ('Muebles TV', 'https://www.sklum.com/es/muebles-tv'),
        ('Camas', 'https://www.sklum.com/es/camas'),
        ('Mesitas de Noche', 'https://www.sklum.com/es/mesitas-noche'),
        ('Sillones', 'https://www.sklum.com/es/sillones'),
        ('Taburetes', 'https://www.sklum.com/es/taburetes'),
        ('Bancos', 'https://www.sklum.com/es/bancos'),
        ('Pufs', 'https://www.sklum.com/es/pufs'),
        ('Exterior', 'https://www.sklum.com/es/exterior'),
        ('Iluminación', 'https://www.sklum.com/es/iluminacion'),
        ('Lámparas de Techo', 'https://www.sklum.com/es/lamparas-techo'),
        ('Lámparas de Mesa', 'https://www.sklum.com/es/lamparas-mesa'),
        ('Espejos', 'https://www.sklum.com/es/espejos'),
        ('Alfombras', 'https://www.sklum.com/es/alfombras'),
        ('Decoración', 'https://www.sklum.com/es/decoracion'),
        ('Textil', 'https://www.sklum.com/es/textil'),
    ]
    
    try:
        status_callback['SKLUM']['message'] = 'Iniciando...'
        await page.goto('https://www.sklum.com/es/', timeout=60000)
        await asyncio.sleep(4)
        
        # Cerrar popups
        for sel in ['button:has-text("Aceptar")', '#onetrust-accept-btn-handler', '.cookie-accept']:
            try:
                btn = await page.query_selector(sel)
                if btn:
                    await btn.click()
                    await asyncio.sleep(1)
                    break
            except:
                pass
        
        # Cerrar popup de newsletter
        try:
            close_btns = await page.query_selector_all('[class*="close"], [aria-label*="close"]')
            for btn in close_btns[:3]:
                try:
                    await btn.click()
                    await asyncio.sleep(0.5)
                except:
                    pass
        except:
            pass
        
        total_cats = len(categories)
        
        for idx, (cat_name, cat_url) in enumerate(categories):
            progress = int(((idx + 1) / total_cats) * 95)
            status_callback['SKLUM']['message'] = f'[{idx+1}/{total_cats}] {cat_name}...'
            status_callback['SKLUM']['progress'] = progress
            
            print(f"\n📂 [{idx+1}/{total_cats}] Sklum: {cat_name}")
            
            try:
                await page.goto(cat_url, timeout=60000)
                await asyncio.sleep(4)
                
                # Scroll
                for _ in range(15):
                    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    await asyncio.sleep(1)
                
                # Extraer productos
                products_data = await page.evaluate("""
                    () => {
                        const products = [];
                        const seenHrefs = new Set();
                        
                        // Sklum usa .html en URLs de productos
                        const links = document.querySelectorAll('a[href*=".html"]');
                        
                        links.forEach(link => {
                            const href = link.href;
                            
                            // Filtrar URLs que no son productos
                            if (!href.includes('/es/') || href.includes('/login') || 
                                href.includes('/cart') || href.includes('/account') ||
                                href.includes('/checkout') || href.includes('/legal') ||
                                href.includes('/cookies') || href.includes('/condiciones')) {
                                return;
                            }
                            
                            if (seenHrefs.has(href)) return;
                            seenHrefs.add(href);
                            
                            let container = link.closest('[class*="product"]') || link.closest('article') || link.parentElement?.parentElement;
                            
                            // Nombre
                            let name = '';
                            if (container) {
                                const nameEl = container.querySelector('h2, h3, [class*="name"], [class*="title"]');
                                if (nameEl) name = nameEl.innerText.trim();
                            }
                            if (!name) {
                                name = link.innerText.trim().split('\\n')[0];
                            }
                            
                            // Imagen
                            let imgSrc = '';
                            if (container) {
                                const img = container.querySelector('img');
                                if (img) imgSrc = img.src || img.dataset.src || '';
                            }
                            
                            // Precio
                            let price = '';
                            if (container) {
                                const priceEl = container.querySelector('[class*="price"]');
                                if (priceEl) price = priceEl.innerText.trim();
                            }
                            
                            if (name && name.length > 3) {
                                products.push({
                                    url: href,
                                    name: name.substring(0, 150),
                                    image: imgSrc,
                                    price: price
                                });
                            }
                        });
                        
                        return products;
                    }
                """)
                
                new_count = 0
                for p in products_data:
                    url = p.get('url', '')
                    if not url or url in seen_urls:
                        continue
                    
                    seen_urls.add(url)
                    new_count += 1
                    
                    price = clean_price(p.get('price', ''))
                    img = p.get('image', '')
                    if img.startswith('//'):
                        img = 'https:' + img
                    
                    all_products.append({
                        'sku_adquify': generate_sku('SKLUM', url, len(all_products)),
                        'supplier_code': 'SKLUM',
                        'name_original': p.get('name', ''),
                        'name_commercial': p.get('name', ''),
                        'category': cat_name,
                        'price_supplier': price,
                        'price_adquify': round(price * 1.28, 2) if price > 0 else 0,
                        'margin': 0.28,
                        'images': [img] if img else [],
                        'product_url': url,
                        'status': 'pending',
                        'source': 'web_scraping',
                        'created_at': datetime.utcnow().isoformat()
                    })
                
                print(f"   ✓ Nuevos: {new_count} | Total: {len(all_products)}")
                await human_delay(1, 2)
                
            except Exception as e:
                print(f"   ✗ Error: {e}")
                continue
        
        status_callback['SKLUM']['message'] = f'✓ {len(all_products)} productos'
        status_callback['SKLUM']['progress'] = 100
        
    except Exception as e:
        print(f"Error general Sklum: {e}")
    
    return all_products

async def scrape_supplier(supplier_code: str, max_pages: int, status_callback: dict) -> List[Dict]:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise Exception("Playwright no instalado")
    
    products = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            locale='es-ES'
        )
        
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        
        page = await context.new_page()
        
        try:
            print(f"\n{'='*60}")
            print(f"🚀 SCRAPER COMPLETO: {supplier_code}")
            print(f"{'='*60}\n")
            
            if supplier_code == 'KAVE':
                products = await scrape_kave_complete(page, status_callback)
            elif supplier_code == 'SKLUM':
                products = await scrape_sklum_complete(page, status_callback)
            else:
                raise Exception(f"No implementado: {supplier_code}")
            
            if products:
                DATA_RAW.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = DATA_RAW / f"{supplier_code.lower()}_full_{timestamp}.json"
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        'supplier': supplier_code,
                        'source': 'web_scraping_full',
                        'extracted_at': datetime.utcnow().isoformat(),
                        'total_products': len(products),
                        'products': products
                    }, f, ensure_ascii=False, indent=2)
                
                print(f"\n{'='*60}")
                print(f"💾 GUARDADO: {output_path}")
                print(f"📦 TOTAL: {len(products)} productos")
                print(f"{'='*60}\n")
                
        finally:
            await browser.close()
    
    return products

if __name__ == "__main__":
    import sys
    
    supplier = sys.argv[1] if len(sys.argv) > 1 else "KAVE"
    status = {supplier: {'status': 'running', 'progress': 0, 'message': ''}}
    
    async def main():
        products = await scrape_supplier(supplier, 100, status)
        print(f"\n✅ {supplier}: {len(products)} productos")
        
        if products:
            cats = {}
            for p in products:
                c = p.get('category', 'Sin')
                cats[c] = cats.get(c, 0) + 1
            print("\n📊 Por categoría:")
            for c, n in sorted(cats.items(), key=lambda x: -x[1]):
                print(f"   {c}: {n}")
    
    asyncio.run(main())
