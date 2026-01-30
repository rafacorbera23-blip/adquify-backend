
import os
import logging
from typing import List, Dict, Optional, Any
from qdrant_client import QdrantClient, AsyncQdrantClient
from qdrant_client.http import models
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("QdrantStore")
logger.setLevel(logging.INFO)

class QdrantHandler:
    """
    Manages interactions with Qdrant Vector Database.
    Target Dimension: 768 (Gemini)
    """
    def __init__(self, collection_name: str = "adquify_products_gemini"):
        # Changed collection name to avoid conflict with old OpenAI one, or user can manually clean.
        # User asked for "Recreation". We can keep same name if we force recreate, or new name.
        # Let's keep a consistent name "adquify_products" but logic to check dimension.
        self.collection_name = "adquify_products" 
        self.url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.api_key = os.getenv("QDRANT_API_KEY", None)
        
        try:
            if self.url == ":memory:":
                # In-memory mode (Local) - Sync only
                self.client = QdrantClient(location=":memory:")
                self.async_client = None
                logger.info("Connected to Qdrant (Memory Mode)")
            else:
                # Server mode
                self.client = QdrantClient(url=self.url, api_key=self.api_key)
                self.async_client = AsyncQdrantClient(url=self.url, api_key=self.api_key)
                logger.info(f"Connected to Qdrant at {self.url}")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            self.client = None
            self.async_client = None

    def ensure_collection(self, vector_size: int = 768, force_recreate: bool = False):
        """
        Ensures the collection exists with correct dimension.
        If size mismatches or force_recreate is True, it deletes and recreates it.
        Default size 768 is for Google models/text-embedding-004.
        """
        if not self.client:
            return

        try:
            collections = self.client.get_collections()
            exists = any(c.name == self.collection_name for c in collections.collections)

            if exists: 
                # Check config
                info = self.client.get_collection(self.collection_name)
                current_size = info.config.params.vectors.size
                
                if current_size != vector_size or force_recreate:
                    logger.warning(f"Collection dimension mismatch or forced (Current: {current_size}, Target: {vector_size}). Recreating...")
                    self.client.delete_collection(self.collection_name)
                    exists = False
                else:
                    logger.debug(f"Collection '{self.collection_name}' exists with correct size.")

            if not exists:
                logger.info(f"Creating collection '{self.collection_name}' with size {vector_size}...")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=vector_size,
                        distance=models.Distance.COSINE
                    )
                )
                logger.info(f"Collection '{self.collection_name}' created.")
                
        except Exception as e:
            logger.error(f"Error checking/creating collection: {e}")

    async def search(self, vector: List[float], limit: int = 5, score_threshold: float = 0.6) -> List[Any]:
        if not self.async_client and not self.client:
             logger.warning("Qdrant client is not initialized.")
             return []
        
        try:
            if self.async_client:
                # Async modern client
                results = await self.async_client.search(
                    collection_name=self.collection_name,
                    query_vector=vector,
                    limit=limit,
                    score_threshold=score_threshold
                )
            else:
                # Sync client (Memory/Local Fallback)
                # Attempt to find the correct search method dynamically to handle version mismatches
                search_method = getattr(self.client, "search", None)
                
                if search_method:
                     # Modern >1.7.0
                     import asyncio
                     results = await asyncio.to_thread(
                        search_method,
                        collection_name=self.collection_name,
                        query_vector=vector,
                        limit=limit,
                        score_threshold=score_threshold
                    )
                else:
                    # Try legacy/alternative methods?
                    # Some versions might expose it under `points` or `search_points`
                    logger.warning("QdrantClient.search not found. Trying points logic or returning empty.")
                    # For now, if 'search' is missing on the main client, it's safer to fallback to SQL 
                    # than to guess obscure API methods which might also crash.
                    # We log clearly to help debug versions.
                    import qdrant_client
                    logger.error(f"INSTALLED QDRANT VERSION: {qdrant_client.__version__}")
                    return []

            return results
        except Exception as e:
            logger.error(f"Search failed with error: {e}")
            return []

    async def upsert_point(self, point_id: str, vector: List[float], payload: Dict):
        if not self.async_client and not self.client:
            return

        try:
            import uuid
            try:
                # Try parsing as UUID
                uuid_obj = uuid.UUID(str(point_id))
                final_id = str(uuid_obj)
            except ValueError:
                # Hash string to UUID
                final_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, str(point_id)))

            points = [
                models.PointStruct(
                    id=final_id,
                    vector=vector,
                    payload=payload
                )
            ]

            if self.async_client:
                await self.async_client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
            else:
                 # Fallback to sync 
                 import asyncio
                 await asyncio.to_thread(
                     self.client.upsert,
                     collection_name=self.collection_name,
                     points=points
                 )
                 
        except Exception as e:
            logger.error(f"Upsert failed for {point_id}: {e}")
