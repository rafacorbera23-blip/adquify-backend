"""
Kave Home Standalone Extractor - Uses Algolia API directly
"""
import requests
import json
from datetime import datetime
from pathlib import Path
import hashlib

DATA_RAW = Path("c:/Treball/1.Negocios/Adquify/adquify-engine/data/raw")

def generate_sku(prefix, url, idx):
    h = hashlib.md5(url.encode()).hexdigest()[:8].upper()
    return f"ADQ-{prefix[:2].upper()}-{h}"

def scrape_kave_full():
    print("🕸️ KAVE HOME (Algolia Full Extraction)")
    
    APP_ID = "EQ79XLPIU7"
    API_KEY = "406dad47edeb9512eb92450bede6ed37"
    INDEX_NAME = "product_es_es"
    
    url = f"https://{APP_ID}-dsn.algolia.net/1/indexes/{INDEX_NAME}/query"
    
    headers = {
        "X-Algolia-API-Key": API_KEY,
        "X-Algolia-Application-Id": APP_ID,
        "Content-Type": "application/json"
    }
    
    SEARCH_TERMS = ["sofas", "sillas", "mesas", "dormitorio", "exterior", "iluminacion", "decoracion"]
    
    products = []
    seen_urls = set()
    
    for term in SEARCH_TERMS:
        print(f"   Fetching '{term}'...")
        page = 0
        
        while True:
            payload = {"params": f"query={term}&hitsPerPage=100&page={page}"}
            
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=30)
                if resp.status_code != 200:
                    print(f"   ❌ Error {resp.status_code}")
                    break
                    
                data = resp.json()
                hits = data.get('hits', [])
                nbPages = data.get('nbPages', 0)
                
                if not hits:
                    break
                
                print(f"     Page {page}/{nbPages-1}: {len(hits)} items")
                
                for hit in hits:
                    try:
                        slug = None
                        if isinstance(hit.get('slug'), dict):
                            slug = hit['slug'].get('es')
                        elif isinstance(hit.get('slug'), str):
                            slug = hit['slug']
                        
                        if not slug:
                            continue
                        
                        full_url = f"https://www.kavehome.com/es/es/{slug}"
                        if full_url in seen_urls:
                            continue
                        seen_urls.add(full_url)
                        
                        # Price
                        price_val = 0.0
                        price_raw = hit.get('price')
                        if isinstance(price_raw, dict):
                            price_raw = price_raw.get('value')
                        if price_raw:
                            try:
                                price_val = float(price_raw)
                            except:
                                pass
                        
                        # Image
                        img = hit.get('mainImage') or hit.get('image') or ''
                        if img and not img.startswith('http'):
                            img = f"https://media.kavehome.com/{img}"
                        
                        # Name
                        name = None
                        if isinstance(hit.get('name'), dict):
                            name = hit['name'].get('es')
                        elif isinstance(hit.get('name'), str):
                            name = hit['name']
                        
                        products.append({
                            'sku_adquify': generate_sku('KAVE', full_url, len(products)),
                            'name_original': name or '',
                            'price_supplier': price_val,
                            'images': [img] if img else [],
                            'product_url': full_url,
                            'source': 'kave_algolia_standalone'
                        })
                    except Exception as e:
                        continue
                
                if page >= nbPages - 1:
                    break
                page += 1
                
            except Exception as e:
                print(f"   ❌ Request Error: {e}")
                break
    
    print(f"\n✅ Total unique products: {len(products)}")
    return products

def save_json(products):
    if not products:
        print("No products to save!")
        return
    
    # Delete old kave files
    for old in DATA_RAW.glob("kave_final_*.json"):
        try:
            old.unlink()
            print(f"🗑️ Deleted: {old.name}")
        except:
            pass
    
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = DATA_RAW / f"kave_final_{ts}.json"
    
    data = {
        'supplier': 'KAVE',
        'date': ts,
        'products': products
    }
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Saved: {path.name} ({len(products)} products)")

if __name__ == "__main__":
    products = scrape_kave_full()
    save_json(products)
