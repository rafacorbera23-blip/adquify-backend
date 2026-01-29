from typing import List
from googlesearch import search
from pydantic import BaseModel

class PotentialSupplier(BaseModel):
    name: str
    url: str
    relevance_score: float

class SupplierHunterAgent:
    """
    The 'Expert Agent'.
    Mission: Search the internet for new suppliers that match hotel needs.
    """
    
    def hunt(self, query: str, num_results: int = 10) -> List[PotentialSupplier]:
        print(f"🕵️‍♀️ Hunting for suppliers: '{query}'...")
        
        # Simulated Google Search (in prod use Seriper or similar API)
        results = []
        try:
            for url in search(query, num_results=num_results):
                # Basic heuristic: if it looks like a shop, keep it
                score = 0.5
                if "tienda" in url or "shop" in url: score += 0.2
                if "hotel" in url or "horeca" in url: score += 0.3
                
                name = url.split("//")[-1].split("/")[0].replace("www.", "")
                
                results.append(PotentialSupplier(
                    name=name,
                    url=url,
                    relevance_score=score
                ))
        except Exception as e:
            print(f"Search error (mocking fallback): {e}")
            # Fallback mock for demo if internet restricted
            results = [
                PotentialSupplier(name="suministros-hoteleros.com", url="https://suministros-hoteleros.com", relevance_score=0.9),
                PotentialSupplier(name="garcia-de-pou.com", url="https://www.garciadepou.com", relevance_score=0.95),
            ]
            
        # Sort by relevance
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results

if __name__ == "__main__":
    hunter = SupplierHunterAgent()
    found = hunter.hunt("proveedores amenities hotel españa")
    for s in found:
        print(f"Found: {s.name} ({s.relevance_score}) - {s.url}")
