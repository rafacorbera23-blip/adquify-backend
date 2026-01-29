import requests
import json

# Kave Home Algolia Config from HTML
APP_ID = "EQ79XLPIU7"
API_KEY = "406dad47edeb9512eb92450bede6ed37"
INDEX_NAME = "product_es_es"

url = f"https://{APP_ID}-dsn.algolia.net/1/indexes/{INDEX_NAME}/query"

headers = {
    "X-Algolia-API-Key": API_KEY,
    "X-Algolia-Application-Id": APP_ID,
    "Content-Type": "application/json"
}

# Query for "sofas" or empty to list all (browse)
payload = {
    "params": "query=&hitsPerPage=20&facets=['*']"
}

try:
    print(f"Sending request to Algolia Index: {INDEX_NAME}...")
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success! Found {data['nbHits']} total hits.")
        print(f"Sample Hit: {json.dumps(data['hits'][0], indent=2)}")
        
        # Check specific category filtering
        print("\n--- Testing Category Filter (Sofas) ---")
        payload_cat = {
            "params": "query=sofas&hitsPerPage=5"
        }
        resp_cat = requests.post(url, headers=headers, json=payload_cat)
        print(f"Category Hits: {resp_cat.json()['nbHits']}")
        
    else:
        print(f"❌ Error {response.status_code}: {response.text}")

except Exception as e:
    print(f"❌ Exception: {e}")
