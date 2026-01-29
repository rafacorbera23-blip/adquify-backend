
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from core.database import SessionLocal
from core.models import Product
from core.ai.embeddings import GeminiEmbeddingHandler
from core.ai.vector_store import QdrantHandler

async def index_catalog():
    print("🚀 Starting Catalog Indexing (Gemini)...")
    
    db: Session = SessionLocal()
    embedder = GeminiEmbeddingHandler()
    vector_store = QdrantHandler()
    
    # Ensure collection with force_recreate if needed (logic in handler handles dimension check)
    vector_store.ensure_collection()
    
    try:
        products = db.query(Product).filter(Product.status == 'published').all()
        print(f"📦 Found {len(products)} published products to index.")
        
        count = 0
        for product in products:
            # Construct text representation for embedding
            # "Silla Velvet Verde - Silla de comedor moderna con terciopelo..."
            text_to_embed = f"{product.name} - {product.description or ''} - Categoría: {product.category}"
            
            try:
                # Generate embedding
                vector = await embedder.get_embedding_async(text_to_embed)
                
                # Payload for Qdrant
                payload = {
                    "id": product.sku_adquify,
                    "name": product.name,
                    "category": product.category,
                    "price": float(product.selling_price) if product.selling_price else 0.0,
                    "supplier_code": product.supplier.code if product.supplier else "UNKNOWN"
                }
                
                # Upsert
                await vector_store.upsert_point(
                    point_id=product.sku_adquify,
                    vector=vector,
                    payload=payload
                )
                
                count += 1
                if count % 10 == 0:
                    print(f"   Indexed {count}/{len(products)}...")
                    
            except Exception as e:
                print(f"❌ Error indexing {product.sku_adquify}: {e}")

        print(f"✅ Indexing Complete! Total indexed: {count}")
        
    finally:
        db.close()

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(index_catalog())
