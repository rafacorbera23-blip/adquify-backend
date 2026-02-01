
import pandas as pd
import json
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from core.database import SessionLocal
from core.models import Product, Supplier, ProductImage

class IngestionService:
    def __init__(self, db: Session):
        self.db = db

    def generate_adquify_sku(self):
        """Generates a unique ADQ- SKU"""
        # Simple implementation using UUID short segment to ensure uniqueness
        # In production, you might want a sequence table or simply a random string check
        return f"ADQ-{uuid.uuid4().hex[:8].upper()}"

    def get_stock_status(self, last_sync: datetime) -> str:
        """Calculates stock status based on time latency"""
        if not last_sync:
            return "red"
        
        delta = datetime.utcnow() - last_sync
        if delta.total_seconds() < 24 * 3600: # < 24h
            return "green"
        elif delta.total_seconds() < 48 * 3600: # < 48h
            return "yellow"
        else:
            return "red"

    def ingest_file(self, file_path: str, supplier_code: str):
        """
        Universal Ingestion Function.
        Reads CSV/JSON/Excel and upserts products.
        """
        # 1. Load Supplier
        supplier = self.db.query(Supplier).filter(Supplier.code == supplier_code).first()
        if not supplier:
            raise ValueError(f"Supplier {supplier_code} not found")

        # 2. Read File
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        elif file_path.endswith('.json'):
            df = pd.read_json(file_path)
        elif file_path.endswith('.xlsx') or file_path.endswith('.xls'):
            df = pd.read_excel(file_path)
        else:
            raise ValueError("Unsupported file format")

        results = {
            "created": 0,
            "updated": 0,
            "total": len(df),
            "errors": []
        }

        # 3. Process Rows
        for index, row in df.iterrows():
            try:
                # Normalize keys (expecting standardized columns or mapping)
                # For this implementation, we assume the input has key columns or we map them.
                # Heuristic mapping for common names:
                sku_supplier = str(row.get('sku_supplier', row.get('sku', row.get('ref', '')))).strip()
                name = row.get('name', row.get('nombre', row.get('title', 'Unknown Product')))
                cost = float(row.get('cost', row.get('coste', row.get('price', 0))))
                stock = int(row.get('stock', row.get('quantity', 0)))
                
                # Metadata extraction (everything else)
                # metadata = row.to_dict() # This might be too heavy?
                # Extract 'specs' if exists
                specs = row.get('specs', {})
                if isinstance(specs, str):
                    try:
                        specs = json.loads(specs)
                    except:
                        specs = {"raw_specs": specs}
                
                # 4. Find or Create Product
                product = self.db.query(Product).filter(
                    Product.supplier_id == supplier.id,
                    Product.sku_supplier == sku_supplier
                ).first()

                is_new = False
                if not product:
                    is_new = True
                    product = Product(
                        sku_adquify=self.generate_adquify_sku(),
                        sku_supplier=sku_supplier,
                        supplier_id=supplier.id,
                        created_at=datetime.utcnow()
                    )
                    self.db.add(product)
                
                # 5. Update Core Fields
                product.name = name
                product.cost_price = cost
                
                # 6. Apply Margin Multiplier
                margin = supplier.margin_multiplier or 1.56
                product.selling_price = cost * margin

                # 7. Update Stock & Sync Status
                product.stock_actual = stock
                product.last_sync = datetime.utcnow()
                product.status_stock = "green" # We just synced it

                # 8. Update Metadata
                # Merge specs into metadata_json
                current_meta = product.metadata_json or {}
                if isinstance(current_meta, str): current_meta = {} # Safety
                current_meta.update(specs)
                
                # Add specific dimensions if present in row
                for dim in ['width', 'height', 'depth', 'weight', 'color', 'ancho', 'alto', 'fondo', 'peso', 'color', 'dimensiones']:
                    if dim in row and pd.notna(row[dim]):
                        current_meta[dim] = row[dim]
                
                product.metadata_json = current_meta
                product.status = "published" # Mark as ready/published if ingested? Or "reviewed"?
                
                if is_new:
                    results["created"] += 1
                else:
                    results["updated"] += 1

            except Exception as e:
                results["errors"].append(f"Row {index}: {str(e)}")
        
        self.db.commit()
        return results

# Helper for standalone execution
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python ingestion.py <file_path> <supplier_code>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    supplier_code = sys.argv[2]
    
    db = SessionLocal()
    try:
        service = IngestionService(db)
        res = service.ingest_file(file_path, supplier_code)
        print(json.dumps(res, indent=2))
    finally:
        db.close()
