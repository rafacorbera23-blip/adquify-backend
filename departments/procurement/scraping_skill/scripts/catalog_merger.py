import pandas as pd
import json
import random
from sqlalchemy.orm import Session
from core.database import SessionLocal, engine
from core.models import Product, Supplier, ProductImage, Base

# Ensure tables exist
Base.metadata.create_all(bind=engine)

class CatalogMergerAgent:
    """
    The 'Internal Catalog Agent'.
    Mission: Read CSVs from different suppliers, normalize, and publish to the Master Catalog.
    """
    
    def __init__(self):
        self.db: Session = SessionLocal()

    def merge_and_publish(self, csv_path: str):
        print(f"🤖 Merger Agent reading: {csv_path}...")
        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            print(f"❌ Error reading CSV: {e}")
            return

        count_new = 0
        count_updated = 0

        for _, row in df.iterrows():
            # 1. Resolve Supplier
            supplier_name = row.get('supplier', 'Unknown')
            supplier = self._get_or_create_supplier(supplier_name)

            # 2. Normalize Data
            name = row.get('name', 'Producto Sin Nombre')
            price_cost = float(row.get('price', 0.0))
            
            # Adquify Logic: Selling Price = Cost * Margin
            price_sale = price_cost * supplier.margin_multiplier
            
            # Dimensions/Specs into JSON
            specs = {
                "materials": row.get('materials'),
                "dimensions": row.get('dimensions'),
                "source": "Agente Scraper V1"
            }

            # 3. Upsert Product (Check by Name + Supplier for now, ideally SKU)
            product = self.db.query(Product).filter(
                Product.name == name, 
                Product.supplier_id == supplier.id
            ).first()

            if product:
                # Update
                product.cost_price = price_cost
                product.selling_price = price_sale
                product.raw_data = specs # Storing specs in raw_data
                count_updated += 1
            else:
                # Create
                product = Product(
                    sku_adquify=f"ADQ-{supplier.code}-{random.randint(10000, 99999)}",
                    sku_supplier=f"SUP-{random.randint(1000, 9999)}", # In real scraper we'd have this
                    supplier_id=supplier.id,
                    name=name,
                    category="Mobiliario", # Inferred or mapped
                    cost_price=price_cost,
                    selling_price=price_sale,
                    description=f"{row.get('materials', '')} - {row.get('dimensions', '')}",
                    status="published",
                    raw_data=specs # Storing specs in raw_data
                )
                self.db.add(product)
                self.db.commit()
                self.db.refresh(product)
                
                # Add Image
                if pd.notna(row.get('image')):
                    img = ProductImage(product_id=product.id, url=row.get('image'))
                    self.db.add(img)
                
                count_new += 1
        
        self.db.commit()
        print(f"✅ Misión Cumplida: {count_new} nuevos, {count_updated} actualizados.")

    def _get_or_create_supplier(self, name: str) -> Supplier:
        # Normalize name
        code = name.upper()[:4]
        supplier = self.db.query(Supplier).filter(Supplier.name == name).first()
        if not supplier:
            supplier = Supplier(
                name=name,
                code=code,
                margin_multiplier=1.35, # Default margin
                login_url=f"https://www.{name.lower().replace(' ', '')}.com"
            )
            self.db.add(supplier)
            self.db.commit()
            self.db.refresh(supplier)
        return supplier

if __name__ == "__main__":
    agent = CatalogMergerAgent()
    agent.merge_and_publish("final_catalog.csv")
