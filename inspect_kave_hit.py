
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

payload = {"params": "query=sofa&hitsPerPage=1"}

try:
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code == 200:
        data = resp.json()
        if data['hits']:
            with open('kave_sample_full.json', 'w', encoding='utf-8') as f:
                json.dump(data['hits'][0], f, indent=2, ensure_ascii=False)
            print("Saved kave_sample_full.json")
    else:
        print(f"Error {resp.status_code}")
except Exception as e:
    print(f"Error: {e}")
