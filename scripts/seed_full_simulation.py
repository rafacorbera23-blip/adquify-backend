import sys
import os
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import SessionLocal, engine
from core.models import Supplier, Product, Order, Client, ProductImage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_simulation_data():
    session = SessionLocal()
    try:
        logger.info("Starting Simulation Seeding...")
        
        # 1. Ensure Client Exists
        client = session.query(Client).first()
        if not client:
            client = Client(name="Hotel Simulation Demo", fiscal_name="Sim Hotel S.L.", cif="B99999999")
            session.add(client)
            session.commit()
            session.refresh(client)
        
        # 2. Get Suppliers (should be ingested already, but verified)
        suppliers = session.query(Supplier).all()
        if not suppliers:
            logger.warning("No suppliers found! Please run ingest_targets.py first. Creating minimal fallback.")
            # Fallback creation if empty
            s1 = Supplier(name="Sklum", code="sklum", status="active", category="FF&E", website="https://sklum.com")
            s2 = Supplier(name="SeniorCare", code="seniorcare", status="active", category="Medical", website="https://seniorcare.es")
            session.add_all([s1, s2])
            session.commit()
            suppliers = session.query(Supplier).all()

        # 3. Seed Products (Rich visual data)
        # We'll map some realistic categories to suppliers
        product_templates = {
            "FF&E": [
                {"name": "Silla Nordic Velvet", "price": 45.00, "img": "https://cdn.sklum.com/es/wk/2479633/silla-nordi-blanco-madera-natural.jpg"},
                {"name": "Sofá 3 Plazas Modular", "price": 450.00, "img": "https://cdn.sklum.com/es/wk/2099395/sofa-modular-de-3-piezas-en-algodon-dhel.jpg"},
                {"name": "Mesa Roble Macizo 200cm", "price": 320.00, "img": "https://cdn.sklum.com/es/wk/2422730/mesa-de-comedor-rectangular-en-madera-de-haya-y-mdf-120x80-cm-royal-design-blanco.jpg"},
                {"name": "Lámpara de Pie Industrial", "price": 89.90, "img": "https://cdn.sklum.com/es/wk/2598858/lampara-de-pie-metalica-meban.jpg"}
            ],
            "Medical": [
                {"name": "Cama Geriátrica Articulada", "price": 1200.00, "img": "https://www.seniorcare.es/wp-content/uploads/2021/06/seniorcare-cama-articulada-carro-elevador-subida.jpg"},
                {"name": "Sillón Relax Eléctrico", "price": 850.00, "img": "https://www.seniorcare.es/wp-content/uploads/2020/02/seniorcare-sillon-relax-power-lift-scaled.jpg"},
                {"name": "Mesita de Noche Hospitalaria", "price": 250.00, "img": "https://www.seniorcare.es/wp-content/uploads/2020/02/seniorcare-mesita-noche-hospital.jpg"}
            ],
            "OS&E": [
                {"name": "Vajilla Porcelana Blanca (Set 6)", "price": 24.00, "img": "https://www.porvasal.es/wp-content/uploads/2019/10/coleccion-triana-porvasal-1.jpg"},
                {"name": "Copa Vino Cristal 50cl", "price": 4.50, "img": "https://www.arcoroc.com/wp-content/uploads/2021/04/C.Kf-Cabernet-Vins-Jeunes-47cl-L9396.jpg"},
                {"name": "Cubertería inox 18/10", "price": 35.00, "img": "https://www.comaspartners.com/images/stories/virtuemart/product/cuberteria-barcelona-comas.jpg"}
            ],
            "Consumibles": [
                {"name": "Gel de Baño Aloe 5L", "price": 12.50, "img": "https://www.bunzlspain.com/images/thumbs/0013919_gel-de-bano-nacarado-5-l_550.jpeg"},
                {"name": "Amenities Kit Dental Bio", "price": 0.45, "img": "https://bio-amenities.com/wp-content/uploads/2021/02/cepillo-dientes-bio.jpg"},
                {"name": "Celulosa Industrial 2 Capas", "price": 18.00, "img": "https://www.bunzlspain.com/images/thumbs/0014051_bobina-industrial-celulosa-pasta-laminada-2-capas-azul_550.jpeg"}
            ]
        }

        logger.info("Seeding Products...")
        count_prod = 0
        for supplier in suppliers:
            # Determine category template to use (fuzzy match)
            cat_key = "FF&E" # Default
            if supplier.category:
                if "Medical" in supplier.category or "Geriátrico" in supplier.notes: cat_key = "Medical"
                if "OS&E" in supplier.category or "Vajilla" in supplier.notes: cat_key = "OS&E"
                if "Consumibles" in supplier.category or "Limpieza" in supplier.notes: cat_key = "Consumibles"
            
            # Add 2-5 random products per supplier to make it look active
            num_products = random.randint(2, 5)
            templates = product_templates.get(cat_key, product_templates["FF&E"])
            
            for _ in range(num_products):
                tmpl = random.choice(templates)
                # Check duplication
                exists = session.query(Product).filter(Product.sku_supplier == f"{supplier.code}-{random.randint(100,999)}").first()
                if exists: continue
                
                prod = Product(
                    name=f"{tmpl['name']} - {supplier.name}",
                    description="Producto simulado para demostración de dashboard.",
                    category=cat_key,
                    cost_price=tmpl['price'] * 0.6,
                    selling_price=tmpl['price'],
                    sku_adquify=f"ADQ-{supplier.code[:3].upper()}-{random.randint(1000,9999)}",
                    sku_supplier=f"{supplier.code}-{random.randint(1000,9999)}",
                    supplier_id=supplier.id,
                    status="published"
                )
                session.add(prod)
                session.flush() # get ID
                
                # Add Image
                if tmpl['img']:
                    img = ProductImage(product_id=prod.id, url=tmpl['img'])
                    session.add(img)
                count_prod += 1
        
        # 4. Seed Orders (Rich stats data)
        logger.info("Seeding Orders...")
        statuses = ["draft", "confirmed", "shipped", "delivered", "cancelled"]
        count_orders = 0
        
        for i in range(25): # 25 Simulation orders
            supplier = random.choice(suppliers)
            days_ago = random.randint(0, 30)
            order_date = datetime.utcnow() - timedelta(days=days_ago)
            
            order = Order(
                order_number=f"ORD-{datetime.now().strftime('%Y')}-{random.randint(10000, 99999)}",
                status=random.choice(statuses),
                total_amount=random.uniform(200.0, 5000.0),
                date=order_date,
                supplier_id=supplier.id,
                client_id=client.id
            )
            session.add(order)
            count_orders += 1
            
        session.commit()
        logger.info(f"Simulation Data Seeded Successfully: {count_prod} Products, {count_orders} Orders.")

    except Exception as e:
        session.rollback()
        logger.error(f"Seeding failed: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    seed_simulation_data()
