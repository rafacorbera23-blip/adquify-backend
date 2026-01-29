import requests
import json

def test_kave_loop():
    APP_ID = "EQ79XLPIU7"
    API_KEY = "406dad47edeb9512eb92450bede6ed37"
    INDEX_NAME = "product_es_es"
    
    url = f"https://{APP_ID}-dsn.algolia.net/1/indexes/{INDEX_NAME}/query"
    
    headers = {
        "X-Algolia-API-Key": API_KEY,
        "X-Algolia-Application-Id": APP_ID,
        "Content-Type": "application/json"
    }
    
    terms = ["sofas"] # Test with one term first
    
    for term in terms:
        print(f"Testing term: {term}")
        page = 0
        total_fetched = 0
        
        while True:
            payload = {
                "params": f"query={term}&hitsPerPage=100&page={page}"
            }
            try:
                print(f"  Requesting page {page}...")
                resp = requests.post(url, headers=headers, json=payload)
                data = resp.json()
                
                hits = data.get('hits', [])
                nbPages = data.get('nbPages', 0)
                nbHits = data.get('nbHits', 0)
                
                print(f"    Status: {resp.status_code}, Hits: {len(hits)}, nbPages: {nbPages}, TotalHits: {nbHits}")
                
                if not hits:
                    print("    No hits, breaking.")
                    break
                
                total_fetched += len(hits)
                
                if page >= nbPages - 1:
                    print("    Reached last page.")
                    break
                    
                page += 1
                
            except Exception as e:
                print(f"    Error: {e}")
                break
        
        print(f"Total fetched for {term}: {total_fetched}")

if __name__ == "__main__":
    test_kave_loop()
