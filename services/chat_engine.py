import asyncio
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from core.models import Product, Supplier
from core.ai.embeddings import GeminiEmbeddingHandler
from core.ai.vector_store import QdrantHandler

class AdquifyChatEngine:
    """
    Real RAG engine for Adquify Catalog.
    Uses Google Gemini Embeddings + Qdrant Vector Search.
    """
    
    def __init__(self, db: Session, vector_store=None):
        self.db = db
        self.embedder = GeminiEmbeddingHandler()
        self.vector_store = vector_store if vector_store else QdrantHandler()
        # Ensure collection exists on startup (async in practice, but fire and forget here or sync check)
        self.vector_store.ensure_collection()

    async def process_query(self, query: str) -> Dict:
        """
        Processes the user query using Semantic Search (RAG).
        """
        # 1. Generate Embedding
        try:
            query_vector = await self.embedder.get_embedding_async(query)
        except Exception as e:
            # Fallback if OpenAI down
            return await self._fallback_sql_search(query)

        # 2. Vector Search (Qdrant)
        search_results = []
        try:
            search_results = await self.vector_store.search(query_vector, limit=5)
        except Exception as e:
            import logging
            logging.error(f"⚠️ Vector Search Failed (Qdrant Error): {e}")
            # Do NOT crash. Just proceed to empty results which triggers fallback.
            search_results = []
        
        # 3. Process Results
        products = []
        if search_results:
            # Extract Product IDs from payloads
            product_ids = [res.payload.get('id') for res in search_results if res.payload]
            
            # Fetch full objects from SQL to ensure freshness (stock, price)
            products = self.db.query(Product).filter(Product.sku_adquify.in_(product_ids)).all()
            
            # Maintain order from vector search
            # Create a map for sorting
            product_map = {p.sku_adquify: p for p in products}
            ordered_products = []
            for pid in product_ids:
                if pid in product_map:
                    ordered_products.append(product_map[pid])
            products = ordered_products

        if not products:
             return await self._fallback_sql_search(query)

        return await self._format_response(products, query)

    async def _fallback_sql_search(self, query: str) -> Dict:
        """
        Legacy SQL search as backup.
        """
        # Simple keyword matching
        products = self.db.query(Product).filter(
            or_(
                Product.name.ilike(f"%{query}%"),
                Product.description.ilike(f"%{query}%")
            )
        ).limit(5).all()
        return await self._format_response(products, query, is_fallback=True)

    async def _format_response(self, products: List[Product], query: str, is_fallback: bool = False) -> Dict:
        if not products:
            return {
                "answer": f"Lo siento, no he encontrado productos que coincidan con '{query}' en el catálogo actual. ¿Pruebas con otros términos?",
                "products": [],
                "pdf_url": None
            }
            
        # Generate PDF
        try:
            from services.pdf_generator import PDFGenerator
            pdf_gen = PDFGenerator()
            # Need to run blocking code in threadpool
            pdf_url = await asyncio.to_thread(pdf_gen.generate_catalog_pdf, products, query)
        except Exception as e:
            print(f"PDF Generation Error: {e}")
            pdf_url = None

        # Generate AI Answer using Gemini Pro
        ai_response_text = ""
        try:
            import google.generativeai as genai
            
            # Context builder
            products_context = "\n".join([
                f"- {p.name} (Precio: €{p.selling_price or 'Consultar'}, Stock: {p.stock_quantity if p.last_stock_update else 'Consultar'})"
                for p in products
            ])
            
            system_prompt = """Eres un vendedor experto de 'Global Prosper', una empresa líder en suministros hoteleros.
Tu tono es profesional, cercano y persuasivo.
Tu objetivo es ayudar al cliente a encontrar lo que necesita y cerrar la venta (o agendar una consulta).
Responde a partir de los productos encontrados en nuestro catálogo.
NO inventes productos. Si no hay información suficiente en los productos listados, sugiere contactar a ventas.
Sé conciso y directo (es WhatsApp)."""

            user_message = f"""Consulta del cliente: "{query}"

Productos encontrados en catálogo:
{products_context}

Genera una respuesta breve, recomendando estos productos. Menciona que se adjunta un PDF con detalles."""
            
            model = genai.GenerativeModel('gemini-1.5-flash')
            # Run blocking generation in thread
            response = await asyncio.to_thread(
                model.generate_content, 
                f"{system_prompt}\n\n{user_message}"
            )
            
            # Defensive check
            if response and hasattr(response, 'text') and response.text:
                ai_response_text = response.text
            else:
                 # Fallback if text generation is blocked or empty
                print("Gemini response was empty or blocked.")
                # DO NOT RAISE, just fallback
                ai_response_text = f"He encontrado {len(products)} opciones para tu búsqueda. Te adjunto el PDF con los detalles."

        except Exception as e:
            print(f"Gemini Generation Error: {e}")
            prefix = "🔍 (Búsqueda por Similitud)" if not is_fallback else "⚠️ (Búsqueda por Palabras Clave)"
            ai_response_text = f"{prefix} He encontrado {len(products)} opciones para '{query}'. Te las he adjuntado en el PDF."

        response = {
            "answer": ai_response_text,
            "pdf_url": pdf_url,
            "products": [
                {
                    "name": p.name,
                    "price": f"€{p.selling_price:.2f}" if p.selling_price else "Consultar",
                    "sku": p.sku_adquify,
                    "image": p.images[0].url if p.images else None,
                    "url": p.raw_data.get('url', '#'),
                    "stock": p.stock_quantity if p.last_stock_update else "Consultar"
                } for p in products
            ]
        }
        return response
