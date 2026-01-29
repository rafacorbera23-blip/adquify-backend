"""
Kave Home Fixed Extractor - Uses correct Algolia fields for COMPLETE product data:
- title: Product name
- price: Price as float
- main_image: Full image URL
- listing_images: Gallery images
- description: Full HTML/Text description
- materials: List of materials
- dimensions: width, height, length
- link: Relative URL
"""
import requests
import json
from datetime import datetime
from pathlib import Path
import hashlib
import time

DATA_RAW = Path("c:/Treball/1.Negocios/Adquify/adquify-engine/data/raw")

def generate_sku(prefix, url, idx):
    h = hashlib.md5(url.encode()).hexdigest()[:8].upper()
    return f"ADQ-{prefix[:2].upper()}-{h}"

def scrape_kave():
    print("🕸️ KAVE HOME (Algolia API - Rich Data)")
    
    APP_ID = "EQ79XLPIU7"
    API_KEY = "406dad47edeb9512eb92450bede6ed37"
    INDEX_NAME = "product_es_es"
    
    url = f"https://{APP_ID}-dsn.algolia.net/1/indexes/{INDEX_NAME}/query"
    
    headers = {
        "X-Algolia-API-Key": API_KEY,
        "X-Algolia-Application-Id": APP_ID,
        "Content-Type": "application/json"
    }
    
    # Broader search terms to cover all categories
    SEARCH_TERMS = ["sofas", "sillas", "mesas", "dormitorio", "exterior", "iluminacion", "decoracion", "almacenaje"]
    
    products = []
    seen_urls = set()
    
    for term in SEARCH_TERMS:
        print(f"   Fetching '{term}'...")
        page = 0
        
        while True:
            # Facets=* ensures we get all data? Actually 'hits' usually contain everything.
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
                        # --- Basic Info ---
                        title = hit.get('title', '')
                        price_val = hit.get('price', 0.0)
                        link = hit.get('link', '')
                        sku_supplier = hit.get('sku', '')
                        
                        if not link:
                            continue
                        
                        full_url = f"https://www.kavehome.com{link}"
                        
                        if full_url in seen_urls:
                            continue
                        seen_urls.add(full_url)
                        
                        # --- Detailed Info ---
                        
                        # Images: Main + Listing
                        images = []
                        main_img = hit.get('main_image')
                        if main_img: images.append(main_img)
                        
                        listing_imgs = hit.get('listing_images', [])
                        for img_obj in listing_imgs:
                             if isinstance(img_obj, dict):
                                img_url = img_obj.get('url')
                                if img_url and img_url not in images:
                                    images.append(img_url)

                        # Description
                        description = hit.get('description', '')
                        
                        # Materials
                        materials_list = hit.get('materials', [])
                        materials = ", ".join(materials_list) if isinstance(materials_list, list) else str(materials_list)
                        
                        # Dimensions
                        width = hit.get('width', '')
                        height = hit.get('height', '')
                        length = hit.get('length', '')
                        dimensions = f"{length}x{width}x{height} cm" if (length and width and height) else ""
                        
                        # Category
                        # 'categories_list' is usually a list of strings
                        cats = hit.get('categories_list', [])
                        category = cats[0] if cats else term
                        
                        # Stock
                        is_out_of_stock = hit.get('is_out_of_stock', False)
                        stock_status = "Out of Stock" if is_out_of_stock else "Available"
                        
                        products.append({
                            'supplier': 'KAVE',
                            'sku_adquify': generate_sku('KAVE', full_url, len(products)),
                            'sku_supplier': sku_supplier,
                            'name': title,
                            'price': float(price_val) if price_val else 0.0,
                            'images': images, # Store as list for JSON, join for CSV later
                            'description': description,
                            'materials': materials,
                            'dimensions': dimensions,
                            'category': category,
                            'stock_status': stock_status,
                            'url': full_url,
                            'source': 'kave_algolia_v3'
                        })
                    except Exception as e:
                        print(f"Error parsing hit: {e}")
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
        'count': len(products),
        'products': products
    }
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    size_mb = path.stat().st_size / (1024 * 1024)
    print(f"💾 Saved: {path.name} ({len(products)} products, {size_mb:.2f} MB)")

if __name__ == "__main__":
    products = scrape_kave()
    save_json(products)
