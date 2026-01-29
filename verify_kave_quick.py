
import requests
import json
from pathlib import Path
from datetime import datetime
import hashlib

DATA_RAW = Path("c:/Treball/1.Negocios/Adquify/adquify-engine/data/raw")

def generate_sku(prefix, url, idx):
    h = hashlib.md5(url.encode()).hexdigest()[:8].upper()
    return f"ADQ-{prefix[:2].upper()}-{h}"

def verify_kave():
    print("🕸️ KAVE QUICK TEST")
    
    APP_ID = "EQ79XLPIU7"
    API_KEY = "406dad47edeb9512eb92450bede6ed37"
    INDEX_NAME = "product_es_es"
    url = f"https://{APP_ID}-dsn.algolia.net/1/indexes/{INDEX_NAME}/query"
    headers = {"X-Algolia-API-Key": API_KEY, "X-Algolia-Application-Id": APP_ID}
    
    products = []
    
    # Just 1 query
    payload = {"params": "query=sillas&hitsPerPage=5"}
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        hits = resp.json().get('hits', [])
        
        for hit in hits:
             products.append({
                'supplier': 'KAVE',
                'sku_adquify': generate_sku('KAVE', hit.get('link',''), len(products)),
                'sku_supplier': hit.get('sku'),
                'name': hit.get('title'),
                'price': float(hit.get('price', 0)),
                'images': [hit.get('main_image')] + [x['url'] for x in hit.get('listing_images',[]) if isinstance(x, dict)],
                'description': hit.get('description', ''),
                'category': 'sillas',
                'url': "https://kavehome.com" + hit.get('link', ''),
                'source': 'kave_quick_test'
             })
        print(f"✅ Got {len(products)} Kave products")
        
    except Exception as e:
        print(f"Error: {e}")
        
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = DATA_RAW / f"kave_final_{ts}_TEST.json"
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({'products': products}, f, indent=2)
    print(f"✅ Saved {path}")

if __name__ == "__main__":
    verify_kave()
