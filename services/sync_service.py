
import logging
from sqlalchemy.orm import Session
from core.models import Product
from core.ai.vector_store import QdrantHandler

logger = logging.getLogger("SyncService")

async def reindex_qdrant_from_db(db: Session, vector_store: QdrantHandler):
    """
    Reads products from SQLite (with cached embeddings) and Upserts them to Qdrant.
    This is used on startup for :memory: Qdrant instances.
    """
    logger.info("Checking Qdrant state...")
    
    # Check if Qdrant is empty (logic could be refined, e.g. count points)
    # For :memory:, we assume it is empty or we force sync.
    # Qdrant client count?
    try:
        # Simple check: do we have any points?
        # vector_store.client.count(...)
        # But let's just do a scroll.
        count = 0
        if vector_store.client:
            res = vector_store.client.count(vector_store.collection_name)
            count = res.count
        
        if count > 0:
            logger.info(f"Qdrant already has {count} points. Skipping re-indexing.")
            return
        
    except Exception as e:
        logger.warning(f"Failed to check Qdrant count: {e}. Proceeding with sync.")

    logger.info("Starting Re-indexing from DB...")
    
    products = db.query(Product).filter(Product.embedding_json.isnot(None)).all()
    logger.info(f"Found {len(products)} products with embeddings in DB.")
    
    for p in products:
        try:
            # Reconstruct payload
            payload = {
                "id": p.sku_adquify,
                "name": p.name,
                "price": p.selling_price,
                "category": p.category,
                "url": p.raw_data.get('url') if p.raw_data else None,
                "stock": p.stock_quantity if p.last_stock_update else "Consultar"
            }
            
            # Upsert
            # Since embedding is stored, we don't need Gemini API
            vector = p.embedding_json
            if vector:
               await vector_store.upsert_point(p.sku_adquify, vector, payload)
               
        except Exception as e:
            logger.error(f"Failed to index product {p.sku_adquify}: {e}")
            
    logger.info("Re-indexing Complete.")
