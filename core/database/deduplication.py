"""
Adquify Engine - Deduplicación Visual
======================================
Detecta productos duplicados usando SKU y similitud de embedding de imagen.
"""

import numpy as np
from typing import List, Tuple, Optional
from sklearn.metrics.pairwise import cosine_similarity
import json
from pathlib import Path

# Umbral de similitud para considerar duplicado (0.95 = muy similar)
SIMILARITY_THRESHOLD = 0.92

def compute_cosine_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """Calcula similitud coseno entre dos embeddings"""
    if not embedding1 or not embedding2:
        return 0.0
    
    vec1 = np.array(embedding1).reshape(1, -1)
    vec2 = np.array(embedding2).reshape(1, -1)
    
    return cosine_similarity(vec1, vec2)[0][0]

def is_duplicate_by_sku(new_sku: str, existing_skus: List[str]) -> bool:
    """Verifica si el SKU ya existe"""
    return new_sku in existing_skus

def find_visual_duplicates(
    new_embedding: List[float], 
    existing_embeddings: List[dict],
    threshold: float = SIMILARITY_THRESHOLD
) -> List[Tuple[str, float]]:
    """
    Encuentra productos visualmente similares.
    
    Args:
        new_embedding: Embedding del nuevo producto
        existing_embeddings: Lista de {"sku": str, "embedding": List[float]}
        threshold: Umbral de similitud (0-1)
    
    Returns:
        Lista de (sku, score) de productos similares
    """
    matches = []
    
    for existing in existing_embeddings:
        sku = existing.get('sku')
        emb = existing.get('embedding')
        
        if not emb:
            continue
        
        score = compute_cosine_similarity(new_embedding, emb)
        
        if score >= threshold:
            matches.append((sku, round(score, 4)))
    
    # Ordenar por similitud descendente
    matches.sort(key=lambda x: x[1], reverse=True)
    return matches

def check_product_duplicate(
    product: dict,
    existing_products: List[dict]
) -> dict:
    """
    Verifica si un producto es duplicado.
    
    Returns:
        {
            "is_duplicate": bool,
            "match_type": "sku" | "visual" | None,
            "matched_sku": str | None,
            "similarity_score": float | None
        }
    """
    new_sku = product.get('sku_supplier')
    new_embedding = product.get('embedding')
    
    # 1. Check SKU exacto
    existing_skus = [p.get('sku_supplier') for p in existing_products if p.get('sku_supplier')]
    if is_duplicate_by_sku(new_sku, existing_skus):
        return {
            "is_duplicate": True,
            "match_type": "sku",
            "matched_sku": new_sku,
            "similarity_score": 1.0
        }
    
    # 2. Check visual si hay embedding
    if new_embedding:
        existing_embeddings = [
            {"sku": p.get('sku_adquify'), "embedding": p.get('embedding')}
            for p in existing_products
            if p.get('embedding')
        ]
        
        visual_matches = find_visual_duplicates(new_embedding, existing_embeddings)
        
        if visual_matches:
            best_match = visual_matches[0]
            return {
                "is_duplicate": True,
                "match_type": "visual",
                "matched_sku": best_match[0],
                "similarity_score": best_match[1]
            }
    
    return {
        "is_duplicate": False,
        "match_type": None,
        "matched_sku": None,
        "similarity_score": None
    }

def deduplicate_batch(
    new_products: List[dict],
    existing_products: List[dict]
) -> dict:
    """
    Procesa un lote de productos y clasifica en nuevos vs duplicados.
    
    Returns:
        {
            "new": List[dict],           # Productos nuevos
            "duplicates": List[dict],    # Productos duplicados (para actualizar)
            "stats": {
                "total": int,
                "new_count": int,
                "duplicate_count": int,
                "sku_matches": int,
                "visual_matches": int
            }
        }
    """
    new_list = []
    duplicates_list = []
    sku_matches = 0
    visual_matches = 0
    
    for product in new_products:
        result = check_product_duplicate(product, existing_products)
        
        if result['is_duplicate']:
            product['_duplicate_info'] = result
            duplicates_list.append(product)
            
            if result['match_type'] == 'sku':
                sku_matches += 1
            elif result['match_type'] == 'visual':
                visual_matches += 1
        else:
            new_list.append(product)
    
    return {
        "new": new_list,
        "duplicates": duplicates_list,
        "stats": {
            "total": len(new_products),
            "new_count": len(new_list),
            "duplicate_count": len(duplicates_list),
            "sku_matches": sku_matches,
            "visual_matches": visual_matches
        }
    }

def generate_mock_embedding(text: str, dim: int = 512) -> List[float]:
    """
    Genera un embedding mock para testing.
    En producción usa CLIP o similar.
    """
    import hashlib
    
    # Crear vector determinístico basado en hash
    h = hashlib.sha256(text.encode()).hexdigest()
    
    # Convertir a floats
    embedding = []
    for i in range(0, min(len(h), dim * 2), 2):
        val = int(h[i:i+2], 16) / 255.0
        embedding.append(val)
    
    # Rellenar si es necesario
    while len(embedding) < dim:
        embedding.append(0.0)
    
    return embedding[:dim]


if __name__ == "__main__":
    # Test
    print("🧪 Test de Deduplicación")
    
    # Simular productos existentes
    existing = [
        {"sku_adquify": "ADQ-001", "sku_supplier": "BB-001", "embedding": generate_mock_embedding("sofa moderno azul")},
        {"sku_adquify": "ADQ-002", "sku_supplier": "BB-002", "embedding": generate_mock_embedding("mesa comedor madera")},
    ]
    
    # Simular nuevos productos
    new_prods = [
        {"sku_supplier": "BB-001", "name": "Sofá Duplicado SKU"},  # Duplicado por SKU
        {"sku_supplier": "BB-003", "name": "Silla Nueva", "embedding": generate_mock_embedding("silla oficina negra")},  # Nuevo
        {"sku_supplier": "BB-004", "name": "Sofá Similar", "embedding": generate_mock_embedding("sofa moderno azul")},  # Duplicado visual
    ]
    
    result = deduplicate_batch(new_prods, existing)
    
    print(f"\n📊 Resultados:")
    print(f"   Total procesados: {result['stats']['total']}")
    print(f"   Nuevos: {result['stats']['new_count']}")
    print(f"   Duplicados: {result['stats']['duplicate_count']}")
    print(f"     - Por SKU: {result['stats']['sku_matches']}")
    print(f"     - Por Visual: {result['stats']['visual_matches']}")
