"""
Debug: Dump raw Algolia response to understand structure
"""
import requests
import json

APP_ID = "EQ79XLPIU7"
API_KEY = "406dad47edeb9512eb92450bede6ed37"
INDEX_NAME = "product_es_es"

url = f"https://{APP_ID}-dsn.algolia.net/1/indexes/{INDEX_NAME}/query"

headers = {
    "X-Algolia-API-Key": API_KEY,
    "X-Algolia-Application-Id": APP_ID,
    "Content-Type": "application/json"
}

payload = {"params": "query=sofas&hitsPerPage=3&page=0"}

resp = requests.post(url, headers=headers, json=payload, timeout=30)
data = resp.json()

# Save full response
with open("kave_algolia_sample.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Response saved. Hits count: {len(data.get('hits', []))}")
print(f"Total hits: {data.get('nbHits', 0)}")

if data.get('hits'):
    print("\n--- First hit structure (keys) ---")
    first = data['hits'][0]
    print(list(first.keys()))
    print("\n--- First hit sample ---")
    print(json.dumps(first, indent=2, ensure_ascii=False)[:2000])
