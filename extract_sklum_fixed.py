"""
Sklum Fixed Extractor - Uses JSON-LD structured data embedded in HTML
Each category page has ItemList with 50 products in JSON-LD format.
"""
import requests
import json
import re
from datetime import datetime
from pathlib import Path
import hashlib
from bs4 import BeautifulSoup

DATA_RAW = Path("c:/Treball/1.Negocios/Adquify/adquify-engine/data/raw")

def generate_sku(prefix, url, idx):
    h = hashlib.md5(url.encode()).hexdigest()[:8].upper()
    return f"ADQ-{prefix[:2].upper()}-{h}"

def scrape_sklum():
    print("🕸️ SKLUM (JSON-LD Extraction)")
    
    # Sklum category IDs
    CATEGORIES = [
        ("633", "sofas"),
        ("543", "sillas"), 
        ("542", "mesas"),
        ("618", "almacenaje"),
        ("527", "dormitorio"),
        ("526", "exterior"),
        ("537", "iluminacion"),
        ("538", "decoracion"),
        ("595", "kids"),
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    }
    
    products = []
    seen_urls = set()
    
    for cat_id, cat_name in CATEGORIES:
        print(f"   Fetching '{cat_name}' (ID: {cat_id})...")
        page = 1
        max_pages = 20  # Safety limit
        
        while page <= max_pages:
            url = f"https://www.sklum.com/es/{cat_id}-comprar-{cat_name}"
            if page > 1:
                url += f"?p={page}"
            
            try:
                resp = requests.get(url, headers=headers, timeout=30)
                if resp.status_code != 200:
                    print(f"     ❌ Error {resp.status_code} for page {page}")
                    break
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Find JSON-LD script with ItemList
                json_ld_scripts = soup.find_all('script', type='application/ld+json')
                
                items_found = 0
                for script in json_ld_scripts:
                    try:
                        data = json.loads(script.string)
                        if isinstance(data, dict) and data.get('@type') == 'ItemList':
                            item_list = data.get('itemListElement', [])
                            
                            for item in item_list:
                                try:
                                    product_data = item.get('item', {})
                                    
                                    product_url = product_data.get('url', '')
                                    if not product_url or product_url in seen_urls:
                                        continue
                                    seen_urls.add(product_url)
                                    
                                    # Extract price from offers
                                    offers = product_data.get('offers', {})
                                    price = 0.0
                                    try:
                                        price = float(offers.get('price', 0))
                                    except:
                                        pass
                                    
                                    # Get image
                                    image = product_data.get('image', '')
                                    
                                    # Get name
                                    name = product_data.get('name', '')
                                    
                                    products.append({
                                        'sku_adquify': generate_sku('SKLUM', product_url, len(products)),
                                        'name_original': name,
                                        'price_supplier': price,
                                        'images': [image] if image else [],
                                        'product_url': product_url,
                                        'source': 'sklum_jsonld'
                                    })
                                    items_found += 1
                                except Exception as e:
                                    continue
                    except json.JSONDecodeError:
                        continue
                
                print(f"     Page {page}: {items_found} items")
                
                if items_found == 0:
                    break
                
                # Check for next page link
                next_link = soup.find('link', rel='next')
                if not next_link:
                    break
                    
                page += 1
                
            except Exception as e:
                print(f"     ❌ Request Error: {e}")
                break
    
    print(f"\n✅ Total unique products: {len(products)}")
    return products

def save_json(products):
    if not products:
        print("No products to save!")
        return
    
    # Delete old sklum files
    for old in DATA_RAW.glob("sklum_final_*.json"):
        try:
            old.unlink()
            print(f"🗑️ Deleted: {old.name}")
        except:
            pass
    
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = DATA_RAW / f"sklum_final_{ts}.json"
    
    data = {
        'supplier': 'SKLUM',
        'date': ts,
        'products': products
    }
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Saved: {path.name} ({len(products)} products)")

if __name__ == "__main__":
    products = scrape_sklum()
    save_json(products)
