
import asyncio
import logging
from core.database import SessionLocal
from services.chat_engine import AdquifyChatEngine
# Ensure we use the same embedding and logic
from api.main import app
from core.ai.vector_store import QdrantHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DebugSearch")

async def main():
    db = SessionLocal()
    # Mocking app state for singleton check if needed, but ChatEngine defaults to new handler if passed None
    # We want to test the EXACT logic
    
    # 1. Init Handler
    qh = QdrantHandler()
    qh.ensure_collection() # Ensure it exists first
    
    # 2. Check if collection has points (Memory mode persistence check)
    count = qh.client.count(qh.collection_name)
    logger.info(f"Qdrant Points Count: {count.count}")
    
    # If empty, we might need to run the re-indexer manually here to simulate valid state
    if count.count == 0:
        logger.warning("Empty Qdrant! Running sync service...")
        from services.sync_service import reindex_qdrant_from_db
        await reindex_qdrant_from_db(db, qh)
        count = qh.client.count(qh.collection_name)
        logger.info(f"Qdrant Points Count after Sync: {count.count}")

    # 3. Simulate Search
    engine = AdquifyChatEngine(db, vector_store=qh)
    query = "mesa de comedor"
    
    logger.info(f"Searching for: '{query}'")
    
    # Inspect embedding
    vector = await engine.embedder.get_embedding_async(query)
    logger.info(f"Vector generated. Length: {len(vector) if vector else 0}")
    
    # Direct Search Call to see Scores
    results = await qh.search(vector, limit=5, score_threshold=0.0) # Check 0 threshold
    
    logger.info("--- RAW RESULTS (Threshold 0.0) ---")
    for r in results:
        logger.info(f"ID: {r.id}, Score: {r.score}, Payload: {r.payload.get('name')}")
        
    # Validated Search (Engine Logic)
    logger.info("--- ENGINE RESPONSE ---")
    final_response = await engine.process_query(query)
    print(final_response)
    
    db.close()

if __name__ == "__main__":
    # Force memory mode for this test
    import os
    os.environ["QDRANT_URL"] = ":memory:"
    asyncio.run(main())
