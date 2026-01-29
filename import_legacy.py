import json
from pathlib import Path
from core.database import SessionLocal
from core.models import Product, Supplier, ProductImage

def import_distrigal():
    db = SessionLocal()
    try:
        # Get Supplier
        supplier = db.query(Supplier).filter(Supplier.code == "distrigal").first()
        if not supplier:
            print("Creating Distrigal supplier...")
            supplier = Supplier(
                code="distrigal", name="Distrigal", margin_multiplier=1.56
            )
            db.add(supplier)
            db.commit()
            
        json_path = Path("distrigal_api_sample.json")
        if not json_path.exists():
            print("No distrigal_api_sample.json found.")
            return

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        print(f"Found {len(data)} items in legacy JSON.")
        
        count = 0
        for item in data:
            sku = item.get('sku')
            if not sku: continue
            
            # Check exist
            existing = db.query(Product).filter(Product.sku_supplier == sku).first()
            if existing: continue
            
            # Price parsing
            try:
                raw_price = float(item['prices']['price']) / 100.0
            except:
                raw_price = 0.0
            
            new_prod = Product(
                sku_supplier=sku,
                sku_adquify=f"ADQ-{abs(hash(sku))}"[:10],
                name=item.get('name'),
                description=item.get('description'),
                cost_price=raw_price,
                selling_price=raw_price * supplier.margin_multiplier,
                supplier_id=supplier.id,
                status='published',
                raw_data=item
            )
            db.add(new_prod)
            db.flush() # To get ID
            
            # Images
            for img_data in item.get('images', []):
                src = img_data.get('src')
                if src:
                    img = ProductImage(product_id=new_prod.id, url=src)
                    db.add(img)
            
            count += 1
        
        db.commit()
        print(f"Imported {count} products from legacy JSON.")

    except Exception as e:
        print(f"Error importing: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import_distrigal()
