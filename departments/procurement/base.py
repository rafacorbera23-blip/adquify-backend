"""
Adquify Engine - Scraper Base
==============================
Clase base para todos los scrapers de proveedores.
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import pandas as pd

class BaseScraper(ABC):
    """Clase base abstracta para scrapers de proveedores"""
    
    def __init__(self, supplier_code: str, supplier_name: str, margin: float = 0.25):
        self.supplier_code = supplier_code
        self.supplier_name = supplier_name
        self.margin = margin
        
        # Paths
        self.engine_root = Path(__file__).parent.parent.parent
        self.data_raw = self.engine_root / "data" / "raw"
        self.assets_images = self.engine_root / "assets" / "images"
        
        # Asegurar directorios
        self.data_raw.mkdir(parents=True, exist_ok=True)
    
    def generate_sku(self, name: str, ref: str, index: int) -> str:
        """Genera SKU único para Adquify"""
        prefix = self.supplier_code[:2].upper()
        hash_part = hashlib.md5(f"{name}{ref}".encode()).hexdigest()[:6].upper()
        return f"ADQ-{prefix}-{hash_part}-{index:04d}"
    
    @staticmethod
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
    
    @abstractmethod
    def extract(self) -> List[Dict]:
        """Extrae productos de la fuente. Debe ser implementado por cada scraper."""
        pass
    
    @abstractmethod
    def generate_render_prompt(self, product: Dict) -> str:
        """Genera prompt de renderizado para el producto."""
        pass
    
    def calculate_price(self, supplier_price: float) -> float:
        """Calcula precio Adquify con margen"""
        return round(supplier_price * (1 + self.margin), 2)
    
    def save_raw_json(self, products: List[Dict]) -> Path:
        """Guarda productos en JSON temporal"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.data_raw / f"{self.supplier_code.lower()}_{timestamp}.json"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                'supplier': self.supplier_code,
                'supplier_name': self.supplier_name,
                'extracted_at': datetime.utcnow().isoformat(),
                'total_products': len(products),
                'products': products
            }, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Guardado: {output_path}")
        return output_path
    
    def run(self, dry_run: bool = True) -> Optional[List[Dict]]:
        """Ejecuta el scraper"""
        print("="*60)
        print(f"🤖 ADQUIFY ENGINE - Scraper {self.supplier_name}")
        print("="*60)
        
        products = self.extract()
        
        if not products:
            print("❌ No se encontraron productos")
            return None
        
        if dry_run:
            print(f"\n🔍 MODO DRY-RUN")
            print(f"   Productos: {len(products)}")
            if products:
                print(f"   Ejemplo:")
                print(json.dumps(products[0], indent=2, ensure_ascii=False))
        else:
            self.save_raw_json(products)
        
        print("\n✅ Completado")
        return products


# Lista de scrapers disponibles
AVAILABLE_SCRAPERS = {
    'BAMBO': {
        'name': 'Bambo Blau',
        'module': 'bambo_blau',
        'excel': 'Sistema Interno GPA AI/output/bambo_catalogo_procesado.xlsx',
        'status': 'active'
    },
    'KAVE': {
        'name': 'Kave Home',
        'module': 'kave_home',
        'excel': 'Sistema Interno GPA AI/output/procesado_Productos_KaveHome_Actualizado_v2.xlsx',
        'status': 'active'
    },
    'SKLUM': {
        'name': 'Sklum',
        'module': 'sklum',
        'website': 'https://www.sklum.com/es/',
        'status': 'pending'
    },
    'MAISONS': {
        'name': 'Maisons du Monde',
        'module': 'maisons_monde',
        'website': 'https://www.maisonsdumonde.com/ES/es',
        'status': 'pending'
    },
    'IKEA': {
        'name': 'IKEA Business',
        'module': 'ikea',
        'website': 'https://www.ikea.com/es/es/business/',
        'status': 'pending'
    }
}

def get_scraper_status() -> List[Dict]:
    """Retorna estado de todos los scrapers"""
    result = []
    for code, info in AVAILABLE_SCRAPERS.items():
        result.append({
            'code': code,
            'name': info['name'],
            'status': info['status'],
            'source': info.get('excel') or info.get('website', 'N/A')
        })
    return result

if __name__ == "__main__":
    print("📋 Scrapers disponibles:")
    for s in get_scraper_status():
        status_icon = "✅" if s['status'] == 'active' else "⏳"
        print(f"   {status_icon} {s['code']}: {s['name']} ({s['status']})")
