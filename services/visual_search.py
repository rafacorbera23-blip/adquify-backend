# import torch
# from sentence_transformers import SentenceTransformer
from PIL import Image
import requests
from io import BytesIO

class VisualSearchService:
    def __init__(self):
        # Load a lightweight CLIP model
        print("Visual Search Disabled (OOM Fix)...")
        self.model = None # SentenceTransformer('clip-ViT-B-32')

    def compute_embedding_from_image(self, image: Image.Image):
        return None
        # try:
        #     return self.model.encode(image).tolist()
        # except Exception as e:
        #     print(f"Error computing embedding: {e}")
        #     return None

    def compute_image_embedding(self, image_url: str):
        return None
        # """Downloads image and computes embedding vector"""
        # try:
        #     response = requests.get(image_url, stream=True)
        #     if response.status_code == 200:
        #         img = Image.open(BytesIO(response.content))
        #         return self.compute_embedding_from_image(img)
        # except Exception as e:
        #     print(f"Error computing embedding for {image_url}: {e}")
        #     return None
    
    def find_similar(self, query_img_path: str, all_embeddings: list):
        return []
        # """
        # Naive search implementation. 
        # In production, use pgvector (SQL) or faiss.
        # """
        # query_img = Image.open(query_img_path)
        # query_emb = self.model.encode(query_img)
        
        # # Cosine similarity logic here...
        # # (Omitted for brevity in this initial setup)
        # pass
