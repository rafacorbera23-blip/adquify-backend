import time
import random
from typing import List, Dict
from core.database import SessionLocal
from core.models import Product, Supplier, ProductImage

# Configuration for the "Big 3" Suppliers per Category
SUPPLIER_REGISTRY = {
    "Mobiliario": [
        {"code": "SKLUM", "name": "Sklum Furniture", "url": "https://www.sklum.com", "type": "dynamic"},
        {"code": "KAVE", "name": "Kave Home", "url": "https://kavehome.com", "type": "dynamic"},
        {"code": "VITRA", "name": "Vitra Design", "url": "https://www.vitra.com", "type": "static"},
    ],
    "Exterior": [
        {"code": "SKLUM", "name": "Sklum Outdoor", "url": "https://www.sklum.com/es/jardin", "type": "dynamic"},
        {"code": "IKEA", "name": "Ikea Garden", "url": "https://www.ikea.com", "type": "static"},
        {"code": "LEROY", "name": "Leroy Merlin", "url": "https://www.leroymerlin.es", "type": "dynamic"},
    ],
    "Consumibles": [
        {"code": "MAKRO", "name": "Makro Horeca", "url": "https://www.makro.es", "type": "static"},
        {"code": "AMZ_BIZ", "name": "Amazon Business", "url": "https://business.amazon.com", "type": "selenium"},
        {"code": "METRO", "name": "Metro Markets", "url": "https://www.metro-markets.com", "type": "static"},
    ]
}

class MassiveImporter:
    """
    The Engine Room for Adquify's Catalog.
    Orchestrates ingestion from diverse sources to create a unified 'One-Stop-Shop'.
    """
    
    def __init__(self):
        self.db = SessionLocal()
        
    def _ensure_supplier(self, s_config: Dict) -> Supplier:
        """Ensures the supplier exists in the DB."""
        supplier = self.db.query(Supplier).filter(Supplier.code == s_config["code"]).first()
        if not supplier:
            print(f"  [+] Registering new supplier: {s_config['name']}")
            supplier = Supplier(
                code=s_config["code"],
                name=s_config["name"],
                login_url=s_config["url"],
                margin_multiplier=1.45 # Standard B2B markup
            )
            self.db.add(supplier)
            self.db.commit()
            self.db.refresh(supplier)
        return supplier

    def run_full_sync(self, categories: List[str] = None):
        """Main entry point to sync catalogs."""
        if not categories:
            categories = SUPPLIER_REGISTRY.keys()
            
        print("🚀 Starting MASSIVE IMPORT process...")
        print(f"🎯 Target Categories: {list(categories)}")
        
        total_imported = 0
        
        for cat in categories:
            if cat not in SUPPLIER_REGISTRY:
                print(f"⚠️ Category {cat} not configured. Skipping.")
                continue
                
            print(f"\n📂 Processing Category: {cat}")
            suppliers = SUPPLIER_REGISTRY[cat]
            
            for s_config in suppliers:
                print(f"  Start Scraping: {s_config['name']} ({s_config['url']})...")
                
                # Here we would call the actual Scraper Classes (Selenium/Soup)
                # For this implementation, we will simulate the ingestion of "Live" data
                
                supplier_entity = self._ensure_supplier(s_config)
                imported_count = self._simulate_scraping(supplier_entity, cat)
                total_imported += imported_count
                
                print(f"  ✅ Imported {imported_count} items from {s_config['name']}")
                
        print("\n" + "="*50)
        print(f"🏁 Import Complete. Total New Items: {total_imported}")
        print("="*50)

    def _simulate_scraping(self, supplier: Supplier, category: str) -> int:
        """
        Simulates finding and saving products. 
        In real production, this connects to `departments/procurement/scrapers/*.py`
        """
        # Mocking data specifically for the standard hotel needs
        mock_products = []
        
        if category == "Consumibles" and supplier.code == "MAKRO":
            mock_products = [
                ("Amenities Shampoo 30ml (Caja 500)", 45.00, "https://images.unsplash.com/photo-1556228720-1987594a8a63?auto=format&fit=crop&q=80&w=600"),
                ("Toalla Mano Algodón Egipcio", 4.50, "https://images.unsplash.com/photo-1616627561839-074385245d47?auto=format&fit=crop&q=80&w=600"),
                ("Kit Limpieza Habitaciones", 12.00, "https://images.unsplash.com/photo-1584620836336-64547c4703f2?auto=format&fit=crop&q=80&w=600")
            ]
        elif category == "Exterior" and supplier.code == "IKEA":
            mock_products = [
                ("Sombrilla Terraza UV+", 89.00, "https://images.unsplash.com/photo-1662369677332-6a56637e7352?auto=format&fit=crop&q=80&w=600"),
                ("Juego Mesa Balcón Acero", 120.00, "https://images.unsplash.com/photo-1595245842183-5858cf85d9c2?auto=format&fit=crop&q=80&w=600")
            ]
        elif category == "Mobiliario":
             # Random procedural gen for furniture
             types = ["Silla", "Mesa", "Estantería"]
             adjectives = ["Nórdica", "Industrial", "Clásica"]
             item = f"{random.choice(types)} {random.choice(adjectives)} {supplier.name}"
             mock_products.append((item, random.randint(50, 200), "https://images.unsplash.com/photo-1592078615290-033ee584e267?auto=format&fit=crop&q=80&w=600"))

        count = 0
        for name, price, img_url in mock_products:
            # Check dupes
            exists = self.db.query(Product).filter(Product.name == name).first()
            if not exists:
                p = Product(
                    sku_adquify=f"ADQ-{supplier.code}-{random.randint(10000,99999)}",
                    sku_supplier=f"SUP-{random.randint(10000,99999)}",
                    supplier_id=supplier.id,
                    name=name,
                    category=category,
                    cost_price=price * 0.7,
                    selling_price=price,
                    status="published"
                )
                self.db.add(p)
                self.db.commit()
                self.db.refresh(p)
                
                # Image
                self.db.add(ProductImage(product_id=p.id, url=img_url))
                self.db.commit()
                count += 1
                
        return count

if __name__ == "__main__":
    importer = MassiveImporter()
    importer.run_full_sync()
