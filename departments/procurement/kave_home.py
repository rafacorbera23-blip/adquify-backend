"""
Adquify Engine - Kave Home Scraper
===================================
Extractor de productos del catálogo Kave Home (Excel procesado).
"""

import os
import json
import hashlib
from datetime import datetime
from pathlib import Path
import pandas as pd

# Paths
ENGINE_ROOT = Path(__file__).parent.parent.parent
DATA_RAW = ENGINE_ROOT / "data" / "raw"
ASSETS_IMAGES = ENGINE_ROOT / "assets" / "images"
EXCEL_PATH = Path("c:/Treball/1.Negocios/Adquify/Sistema Interno GPA AI/output/procesado_Productos_KaveHome_Actualizado_v2.xlsx")

# Configuración
SUPPLIER_CODE = "KAVE"
MARGIN = 0.30  # 30% margen para Kave

def generate_sku(name: str, ref: str, index: int) -> str:
    """Genera SKU único para Adquify"""
    hash_part = hashlib.md5(f"{name}{ref}".encode()).hexdigest()[:6].upper()
    return f"ADQ-KV-{hash_part}-{index:04d}"

def clean_price(price_str) -> float:
    """Limpia y convierte precio a float"""
    if pd.isna(price_str):
        return 0.0
    price_str = str(price_str)
    price_str = price_str.replace('€', '').replace(',', '.').replace(' ', '').strip()
    try:
        return float(price_str)
    except:
        return 0.0

def generate_render_prompt(name: str, description: str, category: str) -> str:
    """Genera prompt descriptivo para renderizado IA"""
    prompt_parts = []
    
    # Detectar tipo de producto por nombre o categoría
    combined = f"{name} {category}".lower() if name and category else ""
    
    if "sofá" in combined or "sofa" in combined:
        prompt_parts.append("Elegant modern sofa")
    elif "silla" in combined or "chair" in combined:
        prompt_parts.append("Designer chair")
    elif "mesa" in combined or "table" in combined:
        prompt_parts.append("Contemporary table")
    elif "lámpara" in combined or "lamp" in combined:
        prompt_parts.append("Modern lighting fixture")
    elif "cama" in combined or "bed" in combined:
        prompt_parts.append("Stylish bed frame")
    elif "estantería" in combined or "shelf" in combined:
        prompt_parts.append("Modular shelving unit")
    elif "armario" in combined or "ward" in combined:
        prompt_parts.append("Spacious wardrobe")
    elif "espejo" in combined or "mirror" in combined:
        prompt_parts.append("Decorative mirror")
    else:
        prompt_parts.append("Modern furniture piece")
    
    # Detectar materiales en descripción
    if description:
        desc_lower = str(description).lower()
        if "madera" in desc_lower or "wood" in desc_lower or "roble" in desc_lower:
            prompt_parts.append("natural wood grain")
        if "metal" in desc_lower or "acero" in desc_lower:
            prompt_parts.append("metal accents")
        if "tela" in desc_lower or "fabric" in desc_lower or "tapizado" in desc_lower:
            prompt_parts.append("upholstered fabric")
        if "mármol" in desc_lower or "marble" in desc_lower:
            prompt_parts.append("marble details")
        if "ratán" in desc_lower or "rattan" in desc_lower:
            prompt_parts.append("rattan texture")
    
    prompt_parts.append("scandinavian design, professional product shot, white background")
    
    return ", ".join(prompt_parts)

def extract_from_excel() -> list:
    """Extrae productos del Excel de Kave Home"""
    
    if not EXCEL_PATH.exists():
        print(f"❌ No se encontró el archivo Excel: {EXCEL_PATH}")
        return []
    
    print(f"📂 Leyendo Excel: {EXCEL_PATH}")
    df = pd.read_excel(EXCEL_PATH)
    
    products = []
    columns = list(df.columns)
    print(f"   Columnas encontradas: {columns[:10]}...")
    
    for idx, row in df.iterrows():
        try:
            # Mapeo flexible de columnas
            name = str(row.iloc[0]) if len(row) > 0 and not pd.isna(row.iloc[0]) else ''
            ref = str(row.iloc[1]) if len(row) > 1 and not pd.isna(row.iloc[1]) else ''
            
            if not name or name == 'nan' or name.startswith('Campo'):
                continue
            
            # Buscar precio y descripción en otras columnas
            price_str = None
            description = ''
            category = ''
            images = []
            
            for i, val in enumerate(row):
                val_str = str(val) if not pd.isna(val) else ''
                # Detectar precio
                if '€' in val_str or (val_str.replace('.','').replace(',','').isdigit() and len(val_str) > 2):
                    if price_str is None:
                        price_str = val_str
                # Detectar URLs de imagen
                if val_str.startswith('http') and ('jpg' in val_str.lower() or 'png' in val_str.lower() or 'webp' in val_str.lower()):
                    images.append(val_str)
                # Detectar descripción larga
                if len(val_str) > 50 and not val_str.startswith('http'):
                    description = val_str
            
            # Procesar
            sku = generate_sku(name, ref, idx)
            price_supplier = clean_price(price_str) if price_str else 0
            price_adquify = round(price_supplier * (1 + MARGIN), 2) if price_supplier > 0 else 0
            render_prompt = generate_render_prompt(name, description, category)
            
            product = {
                'sku_adquify': sku,
                'sku_supplier': ref,
                'supplier_code': SUPPLIER_CODE,
                'name_original': name,
                'name_commercial': name.title(),
                'description': description[:500] if description else '',
                'price_supplier': price_supplier,
                'price_adquify': price_adquify,
                'margin': MARGIN,
                'images': images[:5],  # Max 5 imágenes
                'render_prompt': render_prompt,
                'stock_available': True,
                'created_at': datetime.utcnow().isoformat()
            }
            
            products.append(product)
            
        except Exception as e:
            print(f"⚠️ Error procesando fila {idx}: {e}")
    
    print(f"✅ Extraídos {len(products)} productos de Kave Home")
    return products

def save_raw_json(products: list):
    """Guarda los productos extraídos en JSON temporal"""
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = DATA_RAW / f"kave_home_{timestamp}.json"
    
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
    """Ejecuta el scraper de Kave Home"""
    print("="*60)
    print("🤖 ADQUIFY ENGINE - Scraper Kave Home")
    print("="*60)
    
    # Extraer
    products = extract_from_excel()
    
    if not products:
        print("❌ No se encontraron productos")
        return
    
    if dry_run:
        print("\n🔍 MODO DRY-RUN (sin guardar)")
        print(f"   Productos encontrados: {len(products)}")
        print(f"   Ejemplo:")
        print(json.dumps(products[0], indent=2, ensure_ascii=False))
    else:
        save_raw_json(products)
    
    print("\n✅ Scraping completado")
    return products

if __name__ == "__main__":
    run_scraper(dry_run=True)
