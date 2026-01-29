from core.database import SessionLocal, engine, Base
from core.models import Product, Supplier, ProductImage
import random

# Ensure tables exist
Base.metadata.create_all(bind=engine)

def seed_db():
    db = SessionLocal()
    try:
        # Create Suppliers
        suppliers = [
            {"code": "SKLUM", "name": "Sklum Furniture", "multiplier": 1.45},
            {"code": "KAVE", "name": "Kave Home", "multiplier": 1.50},
            {"code": "Vitra", "name": "Vitra Design", "multiplier": 1.60},
        ]
        
        db_suppliers = {}
        for s in suppliers:
            supplier = db.query(Supplier).filter(Supplier.code == s["code"]).first()
            if not supplier:
                supplier = Supplier(code=s["code"], name=s["name"], margin_multiplier=s["multiplier"])
                db.add(supplier)
                db.commit()
                db.refresh(supplier)
            db_suppliers[s["code"]] = supplier

        # Products Data (High Quality Images)
        products_data = [
            {
                "name": "Sillón Velvet Green",
                "category": "Sillas",
                "price": 120.00,
                "image": "https://images.unsplash.com/photo-1567538096630-e0c55bd6374c?auto=format&fit=crop&q=80&w=600",
                "supplier": "SKLUM"
            },
            {
                "name": "Sofá Modular Gris",
                "category": "Sofas",
                "price": 850.50,
                "image": "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?auto=format&fit=crop&q=80&w=600",
                "supplier": "KAVE"
            },
            {
                "name": "Lámpara Industrial Negra",
                "category": "Iluminación",
                "price": 45.00,
                "image": "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?auto=format&fit=crop&q=80&w=600",
                "supplier": "SKLUM"
            },
            {
                "name": "Mesa Comedor Roble",
                "category": "Mesas",
                "price": 420.00,
                "image": "https://images.unsplash.com/photo-1530018607912-eff2daa1bac4?auto=format&fit=crop&q=80&w=600",
                "supplier": "Vitra"
            },
             {
                "name": "Silla Eames Blanca",
                "category": "Sillas",
                "price": 89.90,
                "image": "https://images.unsplash.com/photo-1519947486511-46149fa0a254?auto=format&fit=crop&q=80&w=600",
                "supplier": "Vitra"
            },
            {
                "name": "Sofá Chetserfield Brown",
                "category": "Sofas",
                "price": 1200.00,
                "image": "https://images.unsplash.com/photo-1540574163026-643ea20ade25?auto=format&fit=crop&q=80&w=600",
                "supplier": "KAVE"
            },
            # --- OUTDOOR ---
            {
                "name": "Tumbona Piscina Rattan",
                "category": "Exterior",
                "price": 150.00,
                "image": "https://images.unsplash.com/photo-1560185007-cde436f6a4d0?auto=format&fit=crop&q=80&w=600",
                "supplier": "SKLUM"
            },
            {
                "name": "Césped Artificial Premium (m2)",
                "category": "Exterior",
                "price": 25.00,
                "image": "https://images.unsplash.com/photo-1585320806297-9794b3e4eeae?auto=format&fit=crop&q=80&w=600",
                "supplier": "SKLUM"
            },
            # --- CONSUMIBLES ---
            {
                 "name": "Pack Papel Higiénico Industrial x48",
                 "category": "Consumibles",
                 "price": 35.50,
                 "image": "https://images.unsplash.com/photo-1584620836336-64547c4703f2?auto=format&fit=crop&q=80&w=600",
                 "supplier": "Vitra" # Placeholder supplier for now
            },
            {
                 "name": "Amenities Kit (Jabón/Champú)",
                 "category": "Consumibles",
                 "price": 0.85,
                 "image": "https://images.unsplash.com/photo-1556228720-1987594a8a63?auto=format&fit=crop&q=80&w=600",
                 "supplier": "KAVE" # Placeholder
            },
            # --- DECORACION ---
             {
                 "name": "Cortina Lino Beige",
                 "category": "Decoracion",
                 "price": 45.00,
                 "image": "https://images.unsplash.com/photo-1513694203232-719a280e022f?auto=format&fit=crop&q=80&w=600",
                 "supplier": "SKLUM"
            }
        ]

        count = 0
        for p_data in products_data:
            # Check if exists
            exists = db.query(Product).filter(Product.name == p_data["name"]).first()
            if not exists:
                prod = Product(
                    sku_adquify=f"ADQ-{random.randint(1000, 9999)}",
                    sku_supplier=f"SUP-{random.randint(1000, 9999)}",
                    supplier_id=db_suppliers[p_data["supplier"]].id,
                    name=p_data["name"],
                    category=p_data["category"],
                    cost_price=p_data["price"] * 0.6,
                    selling_price=p_data["price"],
                    status="published"
                )
                db.add(prod)
                db.commit()
                db.refresh(prod)
                
                # Add Image
                img = ProductImage(product_id=prod.id, url=p_data["image"])
                db.add(img)
                count += 1
        
        db.commit()
        print(f"Seeded {count} new products successfully.")

    except Exception as e:
        print(f"Error seeding DB: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
