
import os
import json
import asyncio
import glob
import time
from pathlib import Path
from typing import List, Dict
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Load Env
load_dotenv()

from core.database import SessionLocal, engine, Base
from core.models import Product, ProductImage, Supplier
from core.ai.embeddings import GeminiEmbeddingHandler
from core.ai.vector_store import QdrantHandler

# Setup Logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ETL_Ingest")

BATCH_SIZE = 10
SLEEP_BETWEEN_BATCHES = 2  # Seconds to respect Gemini Rate Limits

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def ingest_file(file_path: str, db: Session, embedder: GeminiEmbeddingHandler, vector_store: QdrantHandler):
    logger.info(f"Processing File: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read JSON {file_path}: {e}")
        return

    products_list = data.get("products", [])
    if not products_list:
        logger.warning(f"No products found in {file_path}")
        return

    logger.info(f"Found {len(products_list)} products. Starting ingestion...")

    # Process in batches
    for i in range(0, len(products_list), BATCH_SIZE):
        batch = products_list[i : i + BATCH_SIZE]
        logger.info(f"Processing batch {i} to {i+len(batch)}...")

        for p_data in batch:
            try:
                # 1. SQL Ingestion
                sku = p_data.get("sku_adquify") or p_data.get("sku_supplier")
                if not sku:
                    continue

                # Check if exists
                existing_product = db.query(Product).filter(Product.sku_adquify == sku).first()
                
                if existing_product:
                    # Update
                    product = existing_product
                    product.name = p_data.get("name")
                    product.selling_price = p_data.get("price") or 0.0
                    product.description = p_data.get("description")
                    product.stock_quantity = 100 # Mock stock for now if missing
                    # Update other fields as needed
                else:
                    # Create
                    product = Product(
                        sku_adquify=sku,
                        sku_supplier=p_data.get("sku_supplier"),
                        name=p_data.get("name"),
                        description=p_data.get("description"),
                        selling_price=p_data.get("price") or 0.0,
                        stock_quantity=100, # Mock stock
                        supplier_id=1, # Default supplier ID for now or lookup
                        raw_data=p_data,
                        category=p_data.get('category')
                    )
                    db.add(product)
                    db.flush() # Get ID

                # Images
                # (Simplified: clear and re-add or just add if missing. For speed, skipping image logic if already exists)
                if not existing_product and p_data.get("images"):
                    for img_url in p_data.get("images"):
                        db.add(ProductImage(product_id=product.id, url=img_url))

                db.commit()

                # 2. Embedding & Vector Store
                # Construct text for embedding
                text_to_embed = f"{product.name}. {product.description} Category: {p_data.get('category','')}"
                
                # Generate Embedding
                vector = await embedder.get_embedding_async(text_to_embed)
                
                if vector:
                    # Save to DB for caching
                    product.embedding_json = vector
                    db.commit() # Save embedding
                    
                    # Upsert to Qdrant
                    payload = {
                        "id": sku,
                        "name": product.name,
                        "price": product.selling_price,
                        "category": p_data.get("category"),
                        "url": p_data.get("url")
                    }
                    await vector_store.upsert_point(sku, vector, payload)
                
            except Exception as e:
                logger.error(f"Error processing product {p_data.get('sku_adquify')}: {e}")
                db.rollback()
        
        # Rate Limit Sleep
        await asyncio.sleep(SLEEP_BETWEEN_BATCHES)

async def main():
    # Helper Migration
    from sqlalchemy import inspect, text
    try:
        inspector = inspect(engine)
        if "products" in inspector.get_table_names():
            columns = [c["name"] for c in inspector.get_columns("products")]
            with engine.connect() as conn:
                if "stock_quantity" not in columns:
                    logger.info("Adding 'stock_quantity' column...")
                    conn.execute(text("ALTER TABLE products ADD COLUMN stock_quantity INTEGER DEFAULT 0"))
                if "last_stock_update" not in columns:
                    logger.info("Adding 'last_stock_update' column...")
                    conn.execute(text("ALTER TABLE products ADD COLUMN last_stock_update TIMESTAMP"))
                if "embedding_json" not in columns:
                    logger.info("Adding 'embedding_json' column...")
                    conn.execute(text("ALTER TABLE products ADD COLUMN embedding_json TEXT")) # JSON in sqlite is TEXT/JSON
                conn.commit()
    except Exception as e:
        logger.error(f"Migration failed: {e}")

    # Init DB
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Init AI Handlers
    embedder = GeminiEmbeddingHandler()
    vector_store = QdrantHandler()
    vector_store.ensure_collection() # Ensure collection exists

    # Find Files
    root_dir = Path(__file__).parent.parent
    data_dir = root_dir / "data" / "raw"
    files = list(data_dir.glob("*.json"))
    
    if not files:
        logger.error("No JSON files found in data/raw/")
        return

    for file_path in files:
        await ingest_file(str(file_path), db, embedder, vector_store)

    logger.info("Ingestion Complete!")
    db.close()

if __name__ == "__main__":
    asyncio.run(main())
