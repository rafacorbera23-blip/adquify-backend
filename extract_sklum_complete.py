"""
Sklum Complete Extractor - Extracts ALL products from ALL subcategories
VISITS PRODUCT DETAILS to get full images, description, and attributes.
"""
import requests
import requests.adapters
import json
import re
import time
from datetime import datetime
from pathlib import Path
import hashlib
from bs4 import BeautifulSoup

DATA_RAW = Path("c:/Treball/1.Negocios/Adquify/adquify-engine/data/raw")

def generate_sku(prefix, url, idx):
    h = hashlib.md5(url.encode()).hexdigest()[:8].upper()
    return f"ADQ-{prefix[:2].upper()}-{h}"

def get_product_details(url, session):
    """
    Fetches the product detail page and extracts rich data.
    Returns a dict with: description, images (list), materials, dimensions, stock_status
    """
    try:
        # random sleep to be nice
        time.sleep(0.5) 
        resp = session.get(url, timeout=20)
        if resp.status_code != 200:
            return None
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        details = {
            'description': '',
            'images': [],
            'materials': '',
            'dimensions': '',
            'stock_status': 'Available' 
        }
        
        # 1. Try JSON-LD for description and images
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') == 'Product':
                    details['description'] = data.get('description', '')
                    
                    # Images
                    imgs = data.get('image', [])
                    if isinstance(imgs, str): imgs = [imgs]
                    details['images'] = imgs
                    
                    # Stock
                    offers = data.get('offers', {})
                    if isinstance(offers, dict):
                        availability = offers.get('availability', '')
                        if 'OutOfStock' in availability:
                            details['stock_status'] = 'Out of Stock'
                    elif isinstance(offers, list) and len(offers) > 0:
                         # Check first offer
                        availability = offers[0].get('availability', '')
                        if 'OutOfStock' in availability:
                            details['stock_status'] = 'Out of Stock'

                    break 
            except:
                continue

        # 2. Fallback / Additional info from HTML
        
        # Description fallback
        if not details['description']:
            desc_div = soup.select_one('#product-description-short') or soup.select_one('.product-description')
            if desc_div:
                details['description'] = desc_div.get_text(strip=True)

        # Dimensions & Materials (Often in specific blocks)
        # Sklum often puts technical details in a "Technical details" accordion or list
        # Trying generic selectors based on common structure
        
        # Dimensions string (often e.g. "Alto: 80 cm Ancho: 50 cm")
        # Materials usually in the same block
        tech_specs = soup.find(string=re.compile("Material|Dimensiones|Alto|Ancho"))
        if tech_specs:
            parent = tech_specs.find_parent('div') or tech_specs.find_parent('ul')
            if parent:
                full_text = parent.get_text(" ", strip=True)
                # Naive extraction - just dump the text or try to parse ? 
                # For now let's save the text snippet if it's reasonable length
                if len(full_text) < 500:
                    details['materials'] = full_text # It might contain both dimensions and materials
                
        # Better dimensions selector if available (data-sheet)
        data_sheet = soup.select('.data-sheet dl')
        dl_text = []
        for dl in data_sheet:
            dt = dl.find('dt').get_text(strip=True)
            dd = dl.find('dd').get_text(strip=True)
            dl_text.append(f"{dt}: {dd}")
        
        if dl_text:
            # Join all technical specs
            details['dimensions'] = "; ".join(dl_text) 

        return details

    except Exception as e:
        # print(f"Error fetching details for {url}: {e}")
        return None

def scrape_sklum_complete():
    print("🕸️ SKLUM COMPLETE EXTRACTION (DEEP)")
    print("=" * 50)
    
    # ALL Sklum subcategories
    CATEGORIES = [
        # Sofás
        ("633", "sofas"),
        # Reduced list for SAFETY/TIME constraint in this simplified version? 
        # No, user wants ALL. But for testing I might want to start small.
        # I'll keep the full list but maybe add a max_products check per category if needed.
        ("639", "sofa-2-plazas"),
        ("640", "sofa-3-plazas"),
        ("641", "sofas-modulares-2-plazas"),
        ("642", "sofas-modulares-3-plazas"),
        ("643", "sofas-modulares-4-plazas"),
        ("644", "sofas-modulares-5-plazas"),
        ("645", "sofa-cama"),
        ("646", "chaise-longues"),
        ("647", "sofas-5-plazas"),
        ("543", "sillas"),
        ("544", "sillas-de-comedor"),
        ("545", "sillas-oficina"),
        ("548", "banquetas"),
        ("553", "taburetes-altos"),
        ("554", "taburetes-bajos"),
        ("649", "sillones"),
        ("650", "butacas"),
        ("651", "mecedoras"),
        ("699", "puffs"),
        ("542", "mesas"),
        ("555", "mesas-comedor"),
        ("556", "mesas-de-centro"),
        ("557", "mesas-bajas-y-auxiliares"),
        ("558", "mesas-de-escritorio"),
        ("559", "mesas-de-jardin"),
        ("618", "almacenaje"),
        ("619", "estanterias"),
        ("620", "aparadores"),
        ("621", "vitrinas"),
        ("622", "recibidores-y-consolas"),
        ("623", "muebles-tv"),
        ("624", "armarios"),
        ("527", "dormitorio"),
        ("560", "camas"),
        ("561", "cabeceros"),
        ("562", "mesitas-de-noche"),
        ("563", "comodas-y-cajoneras"),
        ("565", "ropa-de-cama"),
        ("537", "iluminacion"),
        ("566", "lamparas-de-techo"),
        ("567", "lamparas-de-pie"),
        ("568", "lamparas-de-mesa"),
        ("569", "apliques-de-pared"),
        ("570", "iluminacion-exterior"),
        ("538", "decoracion"),
        ("571", "espejos"),
        ("572", "alfombras"),
        ("573", "cojines-y-mantas"),
        ("574", "jarrones-y-macetas"),
        ("575", "cuadros-y-laminas"),
        ("576", "relojes"),
        ("577", "velas-y-portavelas"),
        ("526", "exterior"),
        ("578", "sofas-de-exterior"),
        ("579", "sillas-de-exterior"),
        ("580", "mesas-de-exterior"),
        ("581", "tumbonas-y-hamacas"),
        ("582", "sombrillas"),
        ("714", "textil"),
        ("715", "cortinas"),
        ("595", "kids"),
        ("596", "camas-infantiles"),
        ("597", "escritorios-infantiles"),
        ("598", "sillas-infantiles"),
        ("699", "mobiliario-contract"),
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    }
    
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(
        max_retries=requests.adapters.Retry(
            total=5, 
            backoff_factor=2, 
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
    )
    session.mount("https://", adapter)
    session.headers.update(headers)
    
    products = []
    seen_urls = set()
    failed_categories = []
    
    for cat_id, cat_name in CATEGORIES:
        print(f"\n📂 {cat_name} (ID: {cat_id})")
        page = 1
        max_pages = 50 
        
        while page <= max_pages:
            url = f"https://www.sklum.com/es/{cat_id}-comprar-{cat_name}"
            if page > 1:
                url += f"?p={page}"
            
            try:
                resp = session.get(url, timeout=30)
                if resp.status_code == 404:
                    if page == 1: failed_categories.append(cat_name)
                    break
                if resp.status_code != 200:
                    break
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                json_ld_scripts = soup.find_all('script', type='application/ld+json')
                
                items_on_page = []
                for script in json_ld_scripts:
                    try:
                        data = json.loads(script.string)
                        if isinstance(data, dict) and data.get('@type') == 'ItemList':
                            for item in data.get('itemListElement', []):
                                prod = item.get('item', {})
                                p_url = prod.get('url', '')
                                if p_url and p_url not in seen_urls:
                                    seen_urls.add(p_url)
                                    items_on_page.append({
                                        'url': p_url,
                                        'name': prod.get('name', ''),
                                        'sku': prod.get('sku', ''),
                                        'price': prod.get('offers', {}).get('price', 0),
                                        'category': cat_name
                                    })
                    except:
                        continue
                
                if not items_on_page:
                    break
                
                print(f"   Page {page}: Found {len(items_on_page)} items. Fetching details...")
                
                # Fetch details for each item
                for item in items_on_page:
                    try:
                        details = get_product_details(item['url'], session)
                        if details:
                            products.append({
                                'supplier': 'SKLUM',
                                'sku_adquify': generate_sku('SKLUM', item['url'], len(products)),
                                'sku_supplier': item['sku'],
                                'name': item['name'],
                                'price': float(item['price']) if item['price'] else 0.0,
                                'images': details['images'],
                                'description': details['description'],
                                'materials': details['materials'],
                                'dimensions': details['dimensions'],
                                'category': item['category'],
                                'stock_status': details['stock_status'],
                                'url': item['url'],
                                'source': 'sklum_complete_v2'
                            })
                            print(f"     ✅ {item['sku']} - {len(details['images'])} imgs")
                        else:
                            print(f"     ⚠️ Failed details for {item['sku']}")
                    except Exception as e:
                        print(f"     ❌ Error item: {e}")
                
                # Pagination check
                next_link = soup.find('link', rel='next')
                if not next_link:
                    break
                page += 1
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
                break
                
    print(f"\n{'=' * 50}")
    print(f"✅ Total unique products: {len(products)}")
    return products

def save_json(products):
    if not products:
        return
    
    # Delete old sklum files
    for old in DATA_RAW.glob("sklum_*.json"):
        try: old.unlink()
        except: pass
    
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = DATA_RAW / f"sklum_final_{ts}.json"
    
    data = {
        'supplier': 'SKLUM',
        'date': ts,
        'count': len(products),
        'products': products
    }
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    size_mb = path.stat().st_size / (1024 * 1024)
    print(f"💾 Saved: {path.name} ({len(products)} products, {size_mb:.2f} MB)")

if __name__ == "__main__":
    products = scrape_sklum_complete()
    save_json(products)
