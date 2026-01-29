from core.database import engine, Base, SessionLocal
from core.models import Product, Supplier
from harvester.spiders.distrigal import DistrigalHarvester
from services.visual_search import VisualSearchService
from sqlalchemy.orm import Session

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    print("[INFO] Initializing Database Tables...")
    Base.metadata.create_all(bind=engine)
    print("[OK] Database initialized successfully.")

def save_product(db: Session, item: dict, supplier_id: int):
    # Check if exists
    existing = db.query(Product).filter(Product.sku_supplier == item['sku_supplier']).first()
    
    if not existing:
        new_prod = Product(
            sku_supplier=item['sku_supplier'],
            name=item['name'],
            cost_price=item['cost_price'],
            selling_price=item['cost_price'] * 1.56, # Default margin
            supplier_id=supplier_id,
            raw_data=item['raw_data'],
            sku_adquify=f"ADQ-{abs(hash(item['sku_supplier']))}"[:10], # Generate ID
            status='draft'
        )
        db.add(new_prod)
        print(f"   [NEW] {item['name']}")
    else:
        print(f"   [SKIP] {item['name']} (Already exists)")
    
    db.commit()

def main():
    # 1. Init DB
    init_db()
    
    db = SessionLocal()
    
    # 2. Ensure Supplier Exists
    supplier = db.query(Supplier).filter(Supplier.code == "distrigal").first()
    if not supplier:
        supplier = Supplier(code="distrigal", name="Distrigal", margin_multiplier=1.56)
        db.add(supplier)
        db.commit()
    
    # 3. Run Harvester
    print("\n[START] Starting Harvester Pipeline...")
    try:
        harvester = DistrigalHarvester()
        try:
            harvester.start_session(headless=False) 
            harvester.login()
            harvester.extract_products() 
            
            # 4. Save to DB
            print(f"\n[SAVE] Saving {len(harvester.results)} items to Core Database...")
            for item in harvester.results:
                save_product(db, item, supplier.id)
                
        finally:
            harvester.close_session()
    except Exception as e:
        print(f"\n[ERROR] Harvester failed: {e}")
    finally:
        db.close()

    # ... (Distrigal logic above)
    
    # Run Sklum
    print("\n[START] Starting Sklum Harvester...")
    from harvester.spiders.sklum import SklumHarvester
    sklum = SklumHarvester()
    try:
        sklum.start_session(headless=False)
        sklum.login()
        sklum.extract_products()
        
        print(f"\n[SAVE] Saving {len(sklum.results)} Sklum items...")
        
        # Ensure Supplier
        s_sklum = db.query(Supplier).filter(Supplier.code == "sklum").first()
        if not s_sklum:
            s_sklum = Supplier(code="sklum", name="Sklum", margin_multiplier=1.2)
            db.add(s_sklum)
            db.commit()

        for item in sklum.results:
            save_product(db, item, s_sklum.id)
            
    except Exception as e:
        print(f"[ERROR] Sklum failed: {e}")
    finally:
        sklum.close_session()

    print("\n[DONE] Pipeline Completed! Data is in 'adquify_core.db'")
    
    # 5. Fallback Import
    from import_legacy import import_distrigal
    print("\n[INFO] Running Legacy Import to ensure data availability...")
    import_distrigal()

if __name__ == "__main__":
    main()
