import json
import os

raw_dir = "c:/Treball/1.Negocios/Adquify/adquify-engine/data/raw"

for fname in os.listdir(raw_dir):
    if fname.endswith('.json'):
        path = os.path.join(raw_dir, fname)
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            count = len(data.get('products', []))
            print(f"{fname}: {count} products")
