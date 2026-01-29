"""
Adquify Engine - Unified Master Scraper V10
===========================================
Single entry point for ALL suppliers.
- DISTRIGAL: WooCommerce API (Massive & Fast)
- CASATHAI: Robust Playwright Scraper
- KAVE HOME: Stealth Playwright Scraper (New)
- SKLUM: Stealth Playwright Scraper (New)
- BAMBO BLAU: Excel Parser Wrapper
"""

import json
import asyncio
import hashlib
import re
import os
import random
import requests
from datetime import datetime
from pathlib import Path

# Configuración
ENGINE_ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = ENGINE_ROOT / "config" / "suppliers_credentials.json"
DATA_RAW = ENGINE_ROOT / "data" / "raw"

def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"suppliers": {}}

def generate_sku(supplier_code: str, identifier: str, index: int) -> str:
    if identifier and len(identifier) < 30:
        return f"{supplier_code[:3]}-{identifier}".upper().replace(" ", "")
    prefix = supplier_code[:2].upper()
    hash_part = hashlib.md5(f"{identifier}".encode()).hexdigest()[:8].upper()
    return f"ADQ-{prefix}-{hash_part}"

def clean_price(text: str) -> float:
    if not text: return 0.0
    text = str(text).replace('€', '').replace('EUR', '').replace('Puntos', '').replace('&nbsp;', '').strip()
    cleaned = re.sub(r'[^\d,.]', '', text)
    if not cleaned: return 0.0
    if ',' in cleaned and '.' in cleaned:
        if cleaned.rfind('.') > cleaned.rfind(','): 
             cleaned = cleaned.replace(',', '')
        else: 
             cleaned = cleaned.replace('.', '').replace(',', '.')
    elif ',' in cleaned: 
        cleaned = cleaned.replace(',', '.')
    try:
        return float(cleaned)
    except:
        return 0.0

async def scroll_page(page, times=3):
    for _ in range(times):
        await page.evaluate("window.scrollBy(0, window.innerHeight)")
        await asyncio.sleep( random.uniform(0.5, 1.5) )
    await page.evaluate("window.scrollTo(0, 0)")

async def robust_login(page, user_sels, pass_sels, submit_sels, creds):
    try:
        if await page.query_selector(".cookiesplus-accept"):
             await page.click(".cookiesplus-accept", force=True)
    except: pass
    
    for sel in user_sels:
        try:
            if await page.query_selector(sel):
                await page.fill(sel, creds['email'], force=True)
                break
        except: pass
        
    for sel in pass_sels:
        try:
            if await page.query_selector(sel):
                await page.fill(sel, creds['password'], force=True)
                break
        except: pass
        
    for sel in submit_sels:
        try:
            if await page.query_selector(sel):
                await page.click(sel, force=True)
                await page.wait_for_load_state('networkidle')
                return True
        except: pass
    return False

# ==================== DISTRIGAL (API) ====================
def scrape_distrigal_api():
    print("📡 DISTRIGAL (API)")
    base_url = "https://www.distrigalcatalogos.com/wp-json/wc/store/products"
    page = 1
    products = []
    total_pages = 1
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
    
    while page <= total_pages:
        print(f"   Page {page}...", end="\r")
        try:
            resp = requests.get(f"{base_url}?per_page=50&page={page}", headers=headers, timeout=30)
            if resp.status_code != 200: break
            data = resp.json()
            if not data: break
            
            if page == 1:
                total_pages = int(resp.headers.get('X-WP-TotalPages', 1))
            
            for item in data:
                try:
                    price_raw = float(item.get('prices', {}).get('price', 0))
                    minor = int(item.get('prices', {}).get('currency_minor_unit', 2))
                    price = price_raw / (10**minor)
                    
                    products.append({
                        'sku_adquify': generate_sku('DISTRIGAL', str(item.get('id')), len(products)),
                        'name_original': item.get('name', 'Sin nombre'),
                        'price_supplier': price,
                        'images': [i['src'] for i in item.get('images', [])],
                        'product_url': item.get('permalink'),
                        'source': 'api'
                    })
                except: continue
            page += 1
        except: break
    print(f"\n✅ DISTRIGAL: {len(products)} products")
    return products

# ==================== CASA THAI ====================
async def scrape_casathai(context):
    print("🕸️ CASA THAI")
    page = await context.new_page()
    config = load_config()['suppliers']['CASATHAI']
    await page.goto(config['loginUrl'])
    
    await robust_login(page, ["input[name='email']"], ["input[name='password']"], ["#submit-login"], config['credentials'])
    
    products = []
    cats = ["https://casathai.es/es/3-muebles", "https://casathai.es/es/7-sillas", "https://casathai.es/es/15-sofas"]
    
    for cat in cats:
        try:
            current_url = cat
            page_num = 1
            while current_url:
                print(f"   Scanning {cat.split('/')[-1]} Page {page_num}...")
                await page.goto(current_url, timeout=60000)
                await scroll_page(page, 2)
                
                items = await page.query_selector_all(".product-miniature")
                if not items:
                    print("   No items found on this page.")
                    break
                    
                for item in items:
                    try:
                        name_el = await item.query_selector("h2 a")
                        if not name_el: continue
                        name = (await name_el.inner_text()).strip()
                        url = await name_el.get_attribute("href")
                        
                        img_el = await item.query_selector("img")
                        img = ""
                        if img_el:
                            img = await img_el.get_attribute("data-src") or await img_el.get_attribute("src")
                        
                        price = 0.0
                        pe = await item.query_selector(".price")
                        if pe: price = clean_price(await pe.inner_text())
                        
                        products.append({
                            'sku_adquify': generate_sku('CASATHAI', url, len(products)),
                            'name_original': name,
                            'price_supplier': price,
                            'images': [img] if img else [],
                            'product_url': url,
                            'source': 'scraper'
                        })
                    except: continue
                
                # Pagination Logic
                next_btn = await page.query_selector("a.next, a[rel='next'], li.pagination_next a")
                if next_btn:
                    current_url = await next_btn.get_attribute("href")
                    page_num += 1
                else:
                    current_url = None
        except Exception as e:
             print(f"   Error scanning category {cat}: {e}")
    print(f"✅ CASA THAI: {len(products)} products")
    return products

# ==================== KAVE HOME (API) ====================
async def scrape_kave(context=None):
    # Context arg ignored, we use requests
    print("🕸️ KAVE HOME (via Algolia API)")
    import requests
    
    APP_ID = "EQ79XLPIU7"
    API_KEY = "406dad47edeb9512eb92450bede6ed37"
    INDEX_NAME = "product_es_es"
    
    url = f"https://{APP_ID}-dsn.algolia.net/1/indexes/{INDEX_NAME}/query"
    
    headers = {
        "X-Algolia-API-Key": API_KEY,
        "X-Algolia-Application-Id": APP_ID,
        "Content-Type": "application/json"
    }
    
    # Categories to fetch (or empty for all if index allows)
    # We'll use broader searches to be safe
    SEARCH_TERMS = ["sofas", "sillas", "mesas", "dormitorio", "exterior"]
    
    products = []
    seen_urls = set()
    
    for term in SEARCH_TERMS:
        print(f"   Fetching '{term}' from API...")
        page = 0
        while True:
            payload = {
                "params": f"query={term}&hitsPerPage=100&page={page}"
            }
            try:
                resp = requests.post(url, headers=headers, json=payload)
                if resp.status_code != 200:
                    print(f"   Error {resp.status_code}")
                    break
                    
                data = resp.json()
            except Exception as e:
                print(f"   API Request Error: {e}")
                break

            hits = data.get('hits', [])
            if not hits:
                break
            
            print(f"     Page {page}: {len(hits)} items")
            
            for hit in hits:
                try:
                    # Use CORRECT Algolia field names: title, price, main_image, link
                    title = hit.get('title', '')
                    price_val = hit.get('price', 0.0)  # Direct float
                    main_image = hit.get('main_image', '')
                    link = hit.get('link', '')  # e.g., /es/es/p/some-slug
                    
                    if not link:
                        continue
                    
                    full_url = f"https://www.kavehome.com{link}"
                    if full_url in seen_urls:
                        continue
                    seen_urls.add(full_url)
                    
                    products.append({
                        'sku_adquify': generate_sku('KAVE', full_url, len(products)),
                        'name_original': title,
                        'price_supplier': float(price_val) if price_val else 0.0,
                        'images': [main_image] if main_image else [],
                        'product_url': full_url,
                        'source': 'kave_algolia'
                    })
                except Exception as e:
                    continue # Skip bad item
            
            nbPages = data.get('nbPages', 0)
            if page >= nbPages - 1:
                break
            page += 1
                
    print(f"✅ KAVE HOME: {len(products)} products (API)")
    return products

# ==================== SKLUM (Stealth) ====================
async def scrape_sklum(context):
    print("🕸️ SKLUM (Stealth)")
    page = await context.new_page()
    
    await page.goto("https://www.sklum.com/es/")
    try: await page.click("button:has-text('Aceptar')", timeout=3000)
    except: pass
    
    cats = [
        "https://www.sklum.com/es/633-comprar-sofas",
        "https://www.sklum.com/es/543-comprar-sillas",
        "https://www.sklum.com/es/527-comprar-mesas"
    ]
    
    products = []
    seen = set()
    
    for cat in cats:
        print(f"   Scanning {cat.split('/')[-1]}...")
        try:
            await page.goto(cat)
            await asyncio.sleep(3)
            await scroll_page(page, 5)
            
            # --- PAGINATION LOOP ---
            products_found_total = 0
            page_num = 1
            max_pages = 50  # Safety limit
            
            all_items_for_category = [] # Accumulate items for the current category
            
            while page_num <= max_pages:
                print(f"   Scanning page {page_num}...")
                
                # 1. Scroll to trigger lazy loading
                await scroll_page(page, 3) # Scroll a bit to ensure images/elements load
                
                # 2. Extract text from page to find "Load More" buttons if infinite scroll with button
                # Generic "Load More" button clicker for Kave/Sklum
                found_next = False
                try:
                    # Kave Home / Sklum specific load more buttons
                    # Sklum: .js-next-page
                    # Kave: often infinite scroll or button with text "Ver más"
                    load_more_selectors = [
                        '.js-next-page', 
                        'a.load-more', 
                        'button.load-more',
                        'button[class*="load-more"]'
                    ]
                    
                    for sel in load_more_selectors:
                        if await page.locator(sel).count() > 0 and await page.locator(sel).is_visible():
                            print(f"   Found 'Next' button: {sel}. Clicking...")
                            try:
                                await page.locator(sel).first.scroll_into_view_if_needed()
                                await page.locator(sel).first.click(force=True)
                                await page.wait_for_timeout(2000) # Force wait
                                await page.wait_for_load_state('networkidle', timeout=10000)
                            except:
                                print(f"   Click failed for {sel}")
                            
                            found_next = True
                            break
                    
                    # If Kave uses simple infinite scroll without button, we just rely on scrolling, 
                    # but we need to verify if new items appeared.
                    # For now, we assume Sklum needs click, Kave needs scroll.
                    
                except Exception as e:
                    print(f"   Pagination interactions error: {e}")

                # 3. Extract items from CURRENT DOM (Accumulate or just get current set)
                # Since we are likely on a SPA or accumulation page, re-running extraction gets ALL currently visible.
                
                # Sklum Extraction (Revised with correct selector)
                current_items = await page.evaluate("""() => {
                    const results = [];
                    // Sklum Custom Card Selectors
                    const cards = document.querySelectorAll('.c-product-card, .product-miniature, article');
                    cards.forEach(card => {
                        const link = card.querySelector('.c-product-card__title a, .product-title a, a');
                        const img = card.querySelector('.c-product-card__image, img');
                        const price = card.querySelector('.c-product-card__price, .price, .product-price-and-shipping, span[class*="price"]');
                        const name = card.querySelector('.c-product-card__title, .product-title, h3, h2');
                        
                        if(link && name) {
                            results.push({
                                url: link.href,
                                img: img ? (img.dataset.src || img.src) : null,
                                price: price ? price.innerText : '0',
                                name: name.innerText.trim()
                            });
                        }
                    });
                    return results;
                }""")
                
                new_count = len(current_items)
                print(f"   Page {page_num}: Found {new_count} items in DOM.")
                
                # If we have gathered significant items, we might not need to click next if we are relying on scroll 
                # BUT for Sklum, clicking next loads a NEW page or appends.
                
                # FOR SKLUM: It seems it might be standard pagination (URL change or full reload) or Ajax append.
                # If URL changed, we are good.
                
                # Break condition: No "Next" button found AND (no new items appearing via scroll).
                if not found_next:
                    # Attempt one last aggressive scroll
                    prev_height = await page.evaluate("document.body.scrollHeight")
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(4)
                    new_height = await page.evaluate("document.body.scrollHeight")
                    
                    # Check if any new unique items were found in this iteration
                    unique_new_items_count = 0
                    for item in current_items:
                        if item['url'] and item['url'] not in seen:
                            unique_new_items_count += 1

                    if new_height == prev_height and unique_new_items_count == 0:
                        print("   No more content loading (Scroll limit reached and no new unique items).")
                        break # Exit pagination loop
                
                # Add newly found unique items to all_items_for_category
                for item in current_items:
                    if item['url'] and item['url'] not in seen:
                        seen.add(item['url'])
                        all_items_for_category.append(item)
                
                page_num += 1
            
            # Process all accumulated items for this category
            for item in all_items_for_category:
                products.append({
                    'sku_adquify': generate_sku('SKLUM', item['url'], len(products)),
                    'name_original': item['name'],
                    'price_supplier': clean_price(item['price']),
                    'images': [item['img']] if item['img'] else [],
                    'product_url': item['url'],
                    'source': 'scraper_stealth'
                })
        except Exception as e:
             print(f"   Error: {e}")
             
    print(f"✅ SKLUM: {len(products)} products")
    return products

# ==================== BAMBO BLAU ====================
def scrape_bambo_wrapper():
    print("📄 BAMBO BLAU (Excel)")
    # Reusa lógica simplificada del archivo original
    try:
        xl_path = Path("c:/Treball/1.Negocios/Adquify/Sistema Interno GPA AI/output/bambo_catalogo_procesado.xlsx")
        import pandas as pd
        df = pd.read_excel(xl_path)
        products = []
        for _, row in df.iterrows():
            if pd.isna(row.get('Campo2')): continue
            products.append({
               'sku_adquify': generate_sku('BAMBO', str(row.get('Campo3')), len(products)),
               'name_original': row.get('Campo2'),
               'price_supplier': clean_price(row.get('Características', 0)),
               'source': 'excel'
            })
        print(f"✅ BAMBO BLAU: {len(products)} products")
        return products
    except Exception as e:
        print(f"❌ Bamboo Error: {e}")
        return []

# ==================== MAIN ====================
async def run_unified(supplier_arg="ALL"):
    all_products = []
    
    # 1. API Based
    if supplier_arg in ["ALL", "DISTRIGAL"]:
        p = scrape_distrigal_api()
        save_json('DISTRIGAL', p)
        all_products.extend(p)
        
    # 2. Excel Based
    if supplier_arg in ["ALL", "BAMBO"]:
        p = scrape_bambo_wrapper()
        save_json('BAMBO', p)
        all_products.extend(p)
        
    # 3. Browser Based (Stealth)
    if supplier_arg in ["ALL", "CASATHAI", "KAVE", "SKLUM"]:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=['--disable-blink-features=AutomationControlled', '--no-sandbox'] # Stealth basic
            )
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            if supplier_arg in ["ALL", "CASATHAI"]:
                p = await scrape_casathai(context)
                save_json('CASATHAI', p)
                all_products.extend(p)
                
            if supplier_arg in ["ALL", "KAVE"]:
                p = await scrape_kave(context)
                save_json('KAVE', p)
                all_products.extend(p)
                
            if supplier_arg in ["ALL", "SKLUM"]:
                p = await scrape_sklum(context)
                save_json('SKLUM', p)
                all_products.extend(p)
                
            await browser.close()
            
    print(f"\n✨ GRAND TOTAL: {len(all_products)} ITEMS EXTRACTED")
    return all_products

async def run_scraper(supplier_code: str, scraper_status: dict = None):
    """Wrapper compatible with API call"""
    return await run_unified(supplier_code)

def save_json(supplier, products):
    if not products: return
    
    # Cleanup old files for this supplier to prevent duplication in API
    for old_file in DATA_RAW.glob(f"{supplier.lower()}*_final_*.json"):
        try:
            old_file.unlink()
            print(f"🗑️ Deleted old file: {old_file.name}")
        except: pass

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = DATA_RAW / f"{supplier.lower()}_final_{ts}.json"
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({'supplier': supplier, 'date': ts, 'products': products}, f, indent=2)
    print(f"💾 Saved: {path.name}")

if __name__ == "__main__":
    import sys
    arg = sys.argv[1] if len(sys.argv) > 1 else "ALL"
    asyncio.run(run_unified(arg))
