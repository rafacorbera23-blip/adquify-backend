import json
from pathlib import Path

path = Path("c:/Treball/1.Negocios/Adquify/adquify-engine/data/raw/CATALOG_FULL_20260115_191755.json")
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

products = data.get('products', [])
breakdown = {}
for p in products:
    src = p.get('source', 'unknown')
    # Or parsing SKU prefix
    prefix = 'UNK'
    sku = p.get('sku_adquify', '')
    if sku.startswith('ADQ-'):
        parts = sku.split('-')
        if len(parts) > 1: prefix = parts[1]
    elif sku.startswith('REFERENCIA'):
         prefix = 'BAMBOO' # Known pattern for bamboo
    else:
         prefix = 'OTHER'
         
    breakdown[prefix] = breakdown.get(prefix, 0) + 1

print(f"Total: {len(products)}")
print("Breakdown by Supplier (SKU Prefix):")
for k, v in breakdown.items():
    print(f"  {k}: {v}")
