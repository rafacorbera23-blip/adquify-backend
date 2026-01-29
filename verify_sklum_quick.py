
import asyncio
from playwright.async_api import async_playwright
import json
from datetime import datetime
from pathlib import Path
import hashlib

DATA_RAW = Path("c:/Treball/1.Negocios/Adquify/adquify-engine/data/raw")

def generate_sku(prefix, url, idx):
    h = hashlib.md5(url.encode()).hexdigest()[:8].upper()
    return f"ADQ-{prefix[:2].upper()}-{h}"

async def extract_sklum_quick():
    print("🕸️ SKLUM QUICK TEST (Limit 3 items)")
    products = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
        page = await context.new_page()
        
        try:
            # Go to Sklum Sofas
            await page.goto("https://www.sklum.com/es/sofas", timeout=60000)
            product_links = await page.eval_on_selector_all('.product-miniature a:first-child', "els => els.map(e => e.href)")
            
            count = 0
            for p_url in product_links:
                if count >= 3: break
                if 'comprar-' in p_url: continue # skip category links if any
                
                print(f"   Visiting {p_url}...")
                await page.goto(p_url, timeout=60000)
                
                # Extract (Same logic as V2)
                json_data = await page.evaluate("""() => {
                    const script = document.querySelector('script[type="application/ld+json"]');
                    return script ? JSON.parse(script.innerText) : null;
                }""")
                
                name = "Unknown"
                images = []
                desc = ""
                price = 0.0
                
                if json_data and json_data.get('@type') == 'Product':
                    name = json_data.get('name')
                    desc = json_data.get('description', '')
                    img = json_data.get('image', [])
                    images = img if isinstance(img, list) else [img]
                    offers = json_data.get('offers', {})
                    price = float(offers.get('price', 0) if isinstance(offers, dict) else offers[0].get('price', 0))
                
                products.append({
                    'supplier': 'SKLUM',
                    'sku_adquify': generate_sku('SKLUM', p_url, count),
                    'sku_supplier': '',
                    'name': name,
                    'price': price,
                    'images': images,
                    'description': desc,
                    'category': 'sofas',
                    'url': p_url,
                    'source': 'sklum_quick_test'
                })
                count += 1
                
        except Exception as e:
            print(f"Error: {e}")
            
        await browser.close()
        
    # Save
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = DATA_RAW / f"sklum_final_{ts}_TEST.json"
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({'products': products}, f, indent=2)
    print(f"✅ Saved {path}")

if __name__ == "__main__":
    asyncio.run(extract_sklum_quick())
