"""
Casa Thai Full Extractor with Pagination
VISITS PRODUCT DETAILS to get full images, description, and attributes.
"""
from playwright.async_api import async_playwright
import asyncio
import json
from datetime import datetime
from pathlib import Path
import hashlib
import random

DATA_RAW = Path("c:/Treball/1.Negocios/Adquify/adquify-engine/data/raw")

def generate_sku(prefix, url, idx):
    h = hashlib.md5(url.encode()).hexdigest()[:8].upper()
    return f"ADQ-{prefix[:2].upper()}-{h}"

def clean_price(text):
    if not text: return 0.0
    text = text.replace('€', '').replace('.', '').replace(',', '.').strip()
    try:
        return float(text)
    except:
        return 0.0

async def extract_casathai():
    print("🕸️ CASA THAI (Full Extraction - DEEP)")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # Categories to scrape public pages
        categories = [
            "https://casathai.es/es/3-muebles",
            "https://casathai.es/es/7-sillas",
            "https://casathai.es/es/15-sofas", 
            "https://casathai.es/es/12-decoracion",
            "https://casathai.es/es/9-mesas",
            "https://casathai.es/es/18-iluminacion"
        ]
        
        products = []
        seen_urls = set()
        
        for base_url in categories:
            print(f"\n📂 Processing {base_url}...")
            current_page = 1
            
            while True:
                url = f"{base_url}?page={current_page}"
                print(f"   Page {current_page}...")
                
                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                    try:
                        await page.wait_for_selector(".product-miniature", timeout=5000)
                    except:
                        break
                    
                    # collect links first to avoid stale element errors
                    product_links = await page.eval_on_selector_all(".product-miniature .product-title a", "els => els.map(e => e.href)")
                    
                    if not product_links:
                        break
                        
                    items_on_page = []
                    for p_url in product_links:
                         if p_url not in seen_urls:
                             seen_urls.add(p_url)
                             items_on_page.append(p_url)
                             
                    # Visit each product
                    print(f"     Found {len(items_on_page)} new items. Visiting...")
                    
                    for p_url in items_on_page:
                        try:
                            # Open new page/tab for the product to keep listing page safe?
                            # Or just navigate and go back. Navigate might be safer/easier logic if we don't care about back cache.
                            # Let's use a separate page for details or just reuse 'page' and goto
                            
                            p_page = await context.new_page()
                            await p_page.goto(p_url, wait_until='domcontentloaded', timeout=40000)
                            
                            # Extract details
                            name = await p_page.title()
                            name = name.split(" - CasaThai")[0].strip()
                            
                            price_el = await p_page.query_selector('.current-price span[itemprop="price"]')
                            price = clean_price(await price_el.get_attribute("content")) if price_el else 0.0
                            
                            # Description
                            desc_el = await p_page.query_selector('.product-description')
                            description = await desc_el.inner_html() if desc_el else ""
                            
                            # Images
                            images = []
                            img_els = await p_page.query_selector_all('ul.product-images li img')
                            for img in img_els:
                                src = await img.get_attribute('data-image-large-src') or await img.get_attribute('src')
                                if src and src not in images:
                                    images.append(src)
                            
                            # Materials / Features
                            materials = ""
                            dimensions = ""
                            features = await p_page.query_selector_all(".data-sheet dd")
                            for f in features:
                                txt = await f.inner_text()
                                # naive assumption: just dump all features
                                materials += txt + "; "
                            
                            products.append({
                                'supplier': 'CASATHAI',
                                'sku_adquify': generate_sku('CASATHAI', p_url, len(products)),
                                'sku_supplier': '', # Hard to find specific supplier SKU sometimes
                                'name': name,
                                'price': price,
                                'images': images,
                                'description': description,
                                'materials': materials,
                                'dimensions': dimensions, # Often inside features
                                'category': base_url.split('/')[-1],
                                'stock_status': 'Available', # Assume available if listed
                                'url': p_url,
                                'source': 'casathai_full_v2'
                            })
                            
                            await p_page.close()
                            # print(".", end="", flush=True) 
                            
                        except Exception as e:
                            # print(f"x")
                            if not p_page.is_closed(): await p_page.close()
                            continue
                    
                    # Check next button
                    next_btn = await page.query_selector("a.next.disabled")
                    if next_btn:
                        break
                    
                    # explicit check for existing next link
                    has_next = await page.query_selector("a.next")
                    if not has_next:
                        break
                        
                    current_page += 1
                    
                except Exception as e:
                    print(f"Error on page {current_page}: {e}")
                    break
        
        await browser.close()
        
    print(f"\n✅ Total unique products: {len(products)}")
    return products

def save_json(products):
    if not products: return
    
    # Delete old casathai files
    for old in DATA_RAW.glob("casathai_*.json"):
        try: old.unlink() 
        except: pass
    
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = DATA_RAW / f"casathai_final_{ts}.json"
    
    data = {'supplier': 'CASATHAI', 'date': ts, 'count': len(products), 'products': products}
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved: {path.name} ({len(products)} products)")

if __name__ == "__main__":
    asyncio.run(extract_casathai())
