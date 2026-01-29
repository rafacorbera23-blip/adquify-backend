
import os
import logging
import google.generativeai as genai
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("Embeddings")
logger.setLevel(logging.INFO)

class GeminiEmbeddingHandler:
    """
    Handles generation of vector embeddings using Google Generative AI (Gemini).
    Model: models/text-embedding-004
    Dimension: 768
    """
    def __init__(self, model_name: str = "models/text-embedding-004"):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.model_name = model_name
        
        if not self.api_key:
            logger.warning("GOOGLE_API_KEY not found. Embeddings will fail.")
            self.configured = False
        else:
            genai.configure(api_key=self.api_key)
            self.configured = True

    def get_embedding(self, text: str) -> List[float]:
        """
        Synchronous embedding generation.
        """
        if not self.configured:
            raise ValueError("Google API Key not configured")
            
        try:
            # Clean text
            text = text.replace("\n", " ")
            result = genai.embed_content(
                model=self.model_name,
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise e

    async def get_embedding_async(self, text: str) -> List[float]:
        """
        Asynchronous embedding generation (using sync wrapper for now as SDK is sync-first or we delegate to thread).
        """
        # The official python SDK for embeddings currently is often synchronous in its simplest form.
        # We can run it in a thread/executor.
        import asyncio
        return await asyncio.to_thread(self.get_embedding, text)
