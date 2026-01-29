"""
Adquify Engine - Bambo Blau Scraper
====================================
Extractor de productos del catálogo Bambo Blau (Excel).
Basado en la estructura identificada en catalog_structure.json.
"""

import os
import json
import hashlib
import requests
from datetime import datetime
from pathlib import Path
import pandas as pd

# Paths
ENGINE_ROOT = Path(__file__).parent.parent.parent
DATA_RAW = ENGINE_ROOT / "data" / "raw"
ASSETS_IMAGES = ENGINE_ROOT / "assets" / "images"
EXCEL_PATH = Path("c:/Treball/1.Negocios/Adquify/Sistema Interno GPA AI/output/bambo_catalogo_procesado.xlsx")

# Configuración
SUPPLIER_CODE = "BAMBO"
MARGIN = 0.25  # 25% margen

def generate_sku(name: str, ref: str, index: int) -> str:
    """Genera SKU único para Adquify"""
    hash_part = hashlib.md5(f"{name}{ref}".encode()).hexdigest()[:6].upper()
    return f"ADQ-BB-{hash_part}-{index:04d}"

def clean_price(price_str) -> float:
    """Limpia y convierte precio a float"""
    if pd.isna(price_str):
        return 0.0
    price_str = str(price_str)
    price_str = price_str.replace('€', '').replace(',', '.').strip()
    try:
        return float(price_str)
    except:
        return 0.0

def generate_render_prompt(name: str, description: str, dimensions: str) -> str:
    """Genera prompt descriptivo para renderizado IA"""
    prompt_parts = []
    
    # Detectar tipo de producto
    name_lower = name.lower() if name else ""
    if "sofá" in name_lower or "sofa" in name_lower:
        prompt_parts.append("Modern sofa")
    elif "silla" in name_lower:
        prompt_parts.append("Contemporary chair")
    elif "mesa" in name_lower:
        prompt_parts.append("Elegant table")
    elif "lámpara" in name_lower or "lampara" in name_lower:
        prompt_parts.append("Designer lamp")
    elif "cama" in name_lower:
        prompt_parts.append("Comfortable bed")
    elif "armario" in name_lower:
        prompt_parts.append("Storage cabinet")
    else:
        prompt_parts.append("Modern furniture piece")
    
    # Detectar materiales
    if description:
        desc_lower = description.lower()
        if "madera" in desc_lower or "wood" in desc_lower:
            prompt_parts.append("wooden texture")
        if "metal" in desc_lower:
            prompt_parts.append("metal frame")
        if "tela" in desc_lower or "fabric" in desc_lower or "tapizado" in desc_lower:
            prompt_parts.append("upholstered fabric")
        if "cristal" in desc_lower or "glass" in desc_lower:
            prompt_parts.append("glass elements")
        if "mármol" in desc_lower or "marmol" in desc_lower:
            prompt_parts.append("marble surface")
    
    # Añadir dimensiones si existen
    if dimensions and not pd.isna(dimensions):
        prompt_parts.append(f"dimensions {dimensions}")
    
    prompt_parts.append("professional product photography, white background, high resolution")
    
    return ", ".join(prompt_parts)

def download_image(url: str, sku: str, index: int = 0) -> str:
    """Descarga imagen y la guarda localmente"""
    if not url or pd.isna(url):
        return None
    
    try:
        # Crear directorio para el SKU
        sku_dir = ASSETS_IMAGES / sku
        sku_dir.mkdir(parents=True, exist_ok=True)
        
        # Determinar extensión
        ext = "jpg"
        if ".png" in url.lower():
            ext = "png"
        elif ".webp" in url.lower():
            ext = "webp"
        
        local_path = sku_dir / f"img_{index}.{ext}"
        
        # Descargar (simulado para evitar peticiones reales sin permiso)
        # response = requests.get(url, timeout=10)
        # with open(local_path, 'wb') as f:
        #     f.write(response.content)
        
        return str(local_path)
    except Exception as e:
        print(f"⚠️ Error descargando {url}: {e}")
        return None

def extract_from_excel() -> list:
    """Extrae productos del Excel de Bambo Blau"""
    
    if not EXCEL_PATH.exists():
        print(f"❌ No se encontró el archivo Excel: {EXCEL_PATH}")
        return []
    
    print(f"📂 Leyendo Excel: {EXCEL_PATH}")
    df = pd.read_excel(EXCEL_PATH)
    
    products = []
    
    # Mapeo de columnas según catalog_structure.json
    # Campo2 = Nombre, Campo3 = Ref, Campo4-10 = Imágenes, Campo11 = Dimensiones
    # Columna 1 = Descripción, Características = Precio
    
    for idx, row in df.iterrows():
        try:
            name = str(row.get('Campo2', '')) if not pd.isna(row.get('Campo2')) else ''
            ref = str(row.get('Campo3', '')) if not pd.isna(row.get('Campo3')) else ''
            
            if not name or name == 'nan':
                continue
            
            # Extraer imágenes
            images = []
            for i in range(4, 11):
                img_url = row.get(f'Campo{i}')
                if img_url and not pd.isna(img_url) and str(img_url).startswith('http'):
                    images.append(str(img_url))
            
            # Otros campos
            dimensions = str(row.get('Campo11', '')) if not pd.isna(row.get('Campo11')) else ''
            description = str(row.get('Columna 1', '')) if not pd.isna(row.get('Columna 1')) else ''
            price_str = row.get('Características', '')
            
            # Procesar
            sku = generate_sku(name, ref, idx)
            price_supplier = clean_price(price_str)
            price_adquify = round(price_supplier * (1 + MARGIN), 2) if price_supplier > 0 else 0
            render_prompt = generate_render_prompt(name, description, dimensions)
            
            product = {
                'sku_adquify': sku,
                'sku_supplier': ref,
                'supplier_code': SUPPLIER_CODE,
                'name_original': name,
                'name_commercial': name.title().replace('Mod.', 'Modelo'),
                'description': description,
                'dimensions': dimensions,
                'price_supplier': price_supplier,
                'price_adquify': price_adquify,
                'margin': MARGIN,
                'images': images,
                'render_prompt': render_prompt,
                'stock_available': True,
                'created_at': datetime.utcnow().isoformat()
            }
            
            products.append(product)
            
        except Exception as e:
            print(f"⚠️ Error procesando fila {idx}: {e}")
    
    print(f"✅ Extraídos {len(products)} productos de Bambo Blau")
    return products

def save_raw_json(products: list):
    """Guarda los productos extraídos en JSON temporal"""
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = DATA_RAW / f"bambo_blau_{timestamp}.json"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'supplier': SUPPLIER_CODE,
            'extracted_at': datetime.utcnow().isoformat(),
            'total_products': len(products),
            'products': products
        }, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Guardado en: {output_path}")
    return output_path

def run_scraper(dry_run: bool = True):
    """Ejecuta el scraper de Bambo Blau"""
    print("="*60)
    print("🤖 ADQUIFY ENGINE - Scraper Bambo Blau")
    print("="*60)
    
    # Extraer
    products = extract_from_excel()
    
    if not products:
        print("❌ No se encontraron productos")
        return
    
    if dry_run:
        print("\n🔍 MODO DRY-RUN (sin guardar en BD)")
        print(f"   Productos encontrados: {len(products)}")
        print(f"   Ejemplo de producto:")
        print(json.dumps(products[0], indent=2, ensure_ascii=False))
    else:
        # Guardar JSON temporal
        save_raw_json(products)
        
        # TODO: Guardar en BD
        # TODO: Descargar imágenes
        # TODO: Generar embeddings
    
    print("\n✅ Scraping completado")

if __name__ == "__main__":
    # Por defecto en modo dry-run para seguridad
    run_scraper(dry_run=True)
