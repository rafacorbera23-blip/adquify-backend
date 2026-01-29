"""
Adquify Engine - Kave Home Algolia Scraper
==========================================
Extracts products directly from Kave Home's Algolia Index.
Faster, more robust, and doesn't require a browser.
"""

import requests
import json
import hashlib
from datetime import datetime
import asyncio

# Configuración Algolia Kave Home
APP_ID = "EQ79XLPIU7"
API_KEY = "406dad47edeb9512eb92450bede6ed37"
INDEX_NAME = "product_es_es"

SEARCH_TERMS = [
    "sofas", "sillas", "mesas", "muebles tv", 
    "armarios", "estanterias", "camas", "colchones",
    "decoracion", "alfombras", "iluminacion", "exterior"
]

def generate_sku(prefix: str, url: str) -> str:
    """Genera un SKU único basado en la URL"""
    h = hashlib.md5(url.encode()).hexdigest()[:8].upper()
    return f"ADQ-{prefix[:2].upper()}-{h}"

def clean_price(price_data) -> float:
    """Extrae precio numérico"""
    if isinstance(price_data, (int, float)):
        return float(price_data)
    if isinstance(price_data, dict):
        val = price_data.get('value') or price_data.get('price')
        return float(val) if val else 0.0
    return 0.0

async def scrape_kave(scraper_status: dict = None) -> list:
    """
    Ejecuta el scraping de Kave Home vía Algolia API.
    Actualiza scraper_status si se proporciona.
    """
    print("🚀 Iniciando Kave Home Algolia Scraper...")
    
    url = f"https://{APP_ID}-dsn.algolia.net/1/indexes/{INDEX_NAME}/query"
    headers = {
        "X-Algolia-API-Key": API_KEY,
        "X-Algolia-Application-Id": APP_ID,
        "Content-Type": "application/json"
    }

    products = []
    seen_ids = set()
    
    total_terms = len(SEARCH_TERMS)

    for idx, term in enumerate(SEARCH_TERMS):
        if scraper_status:
            progress = int((idx / total_terms) * 90)
            scraper_status['KAVE']['message'] = f"Escaneando categoría: {term} ({idx+1}/{total_terms})"
            scraper_status['KAVE']['progress'] = progress
        
        print(f"   🔎 Buscando: {term}")
        
        page = 0
        hits_per_page = 100
        
        while True:
            # Algolia params
            payload = {
                "params": f"query={term}&hitsPerPage={hits_per_page}&page={page}"
            }
            
            try:
                # Ejecutar request (síncrono pero rápido)
                # Para producción idealmente usar aiohttp, pero requests es aceptable aquí
                resp = requests.post(url, headers=headers, json=payload, timeout=20)
                
                if resp.status_code != 200:
                    print(f"   ❌ Error API {resp.status_code}")
                    break
                    
                data = resp.json()
                hits = data.get('hits', [])
                if page == 0:
                    pass # Debug removed

                nb_pages = data.get('nbPages', 0)
                
                if not hits:
                    break
                
                for hit in hits:
                    try:
                        obj_id = hit.get('objectID')
                        if obj_id in seen_ids:
                            continue
                        seen_ids.add(obj_id)
                        
                        # Extraer datos (Schema corregido)
                        product_url = ""
                        link = hit.get('link')
                        if link:
                            if not link.startswith('http'):
                                product_url = f"https://kavehome.com/{link.lstrip('/')}"
                            else:
                                product_url = link
                        else:
                            # Fallback slug
                            slug_map = hit.get('slug', {})
                            slug = slug_map.get('es', slug_map.get('en', ''))
                            if not slug and isinstance(hit.get('slug'), str):
                                slug = hit.get('slug')
                            if slug:
                                product_url = f"https://kavehome.com/es/es/{slug}"
                        
                        if not product_url:
                            continue
                            
                        name = hit.get('title')
                        if not name:
                            name_map = hit.get('name', {})
                            name = name_map.get('es', name_map.get('en', 'Unknown'))

                        price = clean_price(hit.get('price'))
                        
                        # Imágenes
                        images = []
                        main_img = hit.get('main_image') or hit.get('image')
                        if main_img:
                            if not main_img.startswith('http'):
                                main_img = f"https://media.kavehome.com/{main_img}"
                            images.append(main_img)
                            
                        gallery = hit.get('listing_images') or hit.get('gallery') or []
                        for g in gallery:
                            if isinstance(g, str):
                                if not g.startswith('http'):
                                    g = f"https://media.kavehome.com/{g}"
                                images.append(g)

                        # Categoría
                        category_list = hit.get('category', [])
                        # A veces viene como string o lista
                        if isinstance(category_list, list) and category_list:
                            category = category_list[0]
                        else:
                            category = term.title()

                        # Construir objeto producto (Schema Adquify)
                        sku = generate_sku('KV', product_url)
                        
                        # Descripción
                        desc = hit.get('description') or hit.get('shortDescription', {}).get('es', '')
                        
                        products.append({
                            "sku_adquify": sku,
                            "sku_supplier": str(obj_id),
                            "supplier_code": "KAVE",
                            "name": name,
                            "category": category,
                            "description": desc[:1000] if desc else '',
                            "price_supplier": price, 
                            "currency": "EUR",
                            "url": product_url,
                            "images": images[:5],
                            "raw_data": hit,
                            "extracted_at": datetime.utcnow().isoformat()
                        })
                        
                    except Exception as e:
                        if page == 0 and idx == 0:
                            print(f"   🐛 ERROR PARSING HIT: {e}")
                        continue
                
                page += 1
                if page >= nb_pages:
                    break
                
                # Pequeño delay para no saturar
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"   ❌ Error request: {e}")
                break
    
    print(f"✅ Scraping finalizado. Total productos únicos: {len(products)}")
    return products

if __name__ == "__main__":
    # Test local
    asyncio.run(scrape_kave())
