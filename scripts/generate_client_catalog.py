import sys
import json
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.catalog_processor import AdquifyProcessor

ENGINE_ROOT = Path(__file__).parent.parent
DATA_RAW = ENGINE_ROOT / "data" / "raw"
DATA_EXPORTS = ENGINE_ROOT / "data" / "exports"

# Ensure export directory exists
DATA_EXPORTS.mkdir(parents=True, exist_ok=True)

def get_latest_catalog():
    """Finds the latest CATALOG_FULL_*.json file"""
    files = list(DATA_RAW.glob("CATALOG_FULL_*.json"))
    if not files:
        return None
    return max(files, key=lambda f: f.stat().st_mtime)

def main():
    print("🚀 Iniciando Generación de Catálogo Interactivo Adquify...")
    
    # 1. Load Data
    catalog_file = get_latest_catalog()
    if not catalog_file:
        print("❌ Error: No se encontró ningún archivo de catálogo unificado (CATALOG_FULL_*.json)")
        return
    
    print(f"📂 Cargando catálogo: {catalog_file.name}")
    try:
        with open(catalog_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            products = data.get('products', [])
    except Exception as e:
        print(f"❌ Error leyendo archivo: {e}")
        return

    if not products:
        print("⚠️ El catálogo está vacío.")
        return

    # 2. Process Data
    processor = AdquifyProcessor(products)
    df_result = processor.process()
    
    # 3. Export
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"Catalogo_Maestro_Adquify_Interactive_{timestamp}.csv"
    output_path = DATA_EXPORTS / output_filename
    
    # Also save a "latest" version for easier access
    latest_path = DATA_EXPORTS / "Catalogo_Maestro_Adquify_Interactive_LATEST.csv"
    
    print(f"💾 Guardando {len(df_result)} productos procesados...")
    df_result.to_csv(output_path, index=False, encoding='utf-8-sig') # sig for Excel compatibility
    df_result.to_csv(latest_path, index=False, encoding='utf-8-sig')
    
    print(f"✅ ¡Hecho! Archivo generado: {output_path}")
    print(f"📊 Preview:\n{df_result.head()}")

if __name__ == "__main__":
    main()
