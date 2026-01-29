"""
Unified Catalog Updater
Orchestrates all scrapers and updates local JSON database and EXPORTS TO CSV/EXCEL.
"""
import subprocess
import sys
import json
import time
import csv
from pathlib import Path
from datetime import datetime

# Check for pandas/openpyxl
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

# Script paths
SCRIPTS = {
    "KAVE": "extract_kave_fixed.py",
    "SKLUM": "extract_sklum_v2.py", # Updated to new playwright version
    "CASATHAI": "extract_casathai_full.py",
}

DATA_RAW = Path("c:/Treball/1.Negocios/Adquify/adquify-engine/data/raw")

def run_script(name, script_name):
    print(f"\n🚀 STARTING {name} UPDATE...")
    try:
        if not Path(script_name).exists():
            print(f"   ⚠️ Script {script_name} not found. Skipping.")
            return False
            
        start = time.time()
        # Run with explicit python
        result = subprocess.run(
            [sys.executable, script_name], 
            capture_output=True, 
            text=True, 
            cwd="c:/Treball/1.Negocios/Adquify/adquify-engine",
            timeout=14400 
        )
        duration = time.time() - start
        
        if result.returncode == 0:
            print(f"   ✅ {name} SUCCESS ({duration:.1f}s)")
            for line in result.stdout.splitlines():
                if "✅" in line or "💾" in line:
                    print(f"      {line.strip()}")
            return True
        else:
            print(f"   ❌ {name} FAILED (Exit Code: {result.returncode})")
            # print(f"      Error: {result.stderr[:200]}...")
            # print(f"      Output: {result.stdout[-200:]}...")
            # Print more error context
            print(f"      STDERR:\n{result.stderr}")
            return False
            
    except Exception as e:
        print(f"   ❌ {name} ERROR: {str(e)}")
        return False

def export_data(products, basename):
    if not products:
        return

    # 1. Export CSV
    csv_path = basename.with_suffix('.csv')
    print(f"   📊 Exporting to CSV: {csv_path.name}...")
    
    fieldnames = [
        'supplier', 'sku_adquify', 'sku_supplier', 'name', 'price', 
        'stock_status', 'category', 'dimensions', 'materials',
        'images', 'description', 'url', 'source'
    ]
    
    # Pre-process for CSV (strings instead of lists)
    csv_rows = []
    for p in products:
        row = p.copy()
        if isinstance(row.get('images'), list):
            row['images'] = " | ".join(row['images']) # Pipe separator for multiple images
        csv_rows.append(row)

    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(csv_rows)
            
    size_mb = csv_path.stat().st_size / (1024 * 1024)
    print(f"      ✅ CSV Saved ({size_mb:.2f} MB)")

    # 2. Export Excel (if pandas available)
    if HAS_PANDAS:
        xlsx_path = basename.with_suffix('.xlsx')
        print(f"   📊 Exporting to EXCEL: {xlsx_path.name}...")
        try:
            df = pd.DataFrame(products)
            # Ensure images are stringified for verification
            df['images'] = df['images'].apply(lambda x: " | ".join(x) if isinstance(x, list) else x)
            # Reorder columns
            cols = [c for c in fieldnames if c in df.columns]
            df = df[cols]
            
            df.to_excel(xlsx_path, index=False, engine='openpyxl')
            size_mb = xlsx_path.stat().st_size / (1024 * 1024)
            print(f"      ✅ Excel Saved ({size_mb:.2f} MB)")
        except Exception as e:
            print(f"      ⚠️ Excel Export Failed: {e}")
    else:
        print("      ⚠️ Pandas not installed, skipping Excel export.")

def consolidate_data():
    print("\n📦 CONSOLIDATING DATA...")
    all_products = []
    
    # Helper to load latest
    def load_latest(pattern, name):
        try:
            files = list(DATA_RAW.glob(pattern))
            if files:
                latest = max(files, key=lambda f: f.stat().st_mtime)
                with open(latest, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    prods = data.get('products', [])
                    print(f"   • {name}: {len(prods)} products")
                    return prods
        except Exception as e:
            print(f"   ⚠️ {name} Error: {e}")
        return []

    all_products.extend(load_latest("kave_final_*.json", "Kave Home"))
    all_products.extend(load_latest("sklum_final_*.json", "Sklum"))
    all_products.extend(load_latest("casathai_final_*.json", "Casa Thai"))
    all_products.extend(load_latest("*distrigal*.json", "Distrigal"))
    
    print(f"\n✅ TOTAL CONSOLIDATED CATALOG: {len(all_products)} products")
    
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save Master JSON
    path_json = DATA_RAW / f"CATALOG_FULL_{ts}.json"
    with open(path_json, 'w', encoding='utf-8') as f:
        json.dump({'date': ts, 'count': len(all_products), 'products': all_products}, f, indent=2, ensure_ascii=False)
    print(f"💾 JSON saved: {path_json.name}")
    
    # Export CSV/Excel
    export_data(all_products, DATA_RAW / f"CATALOG_FULL_{ts}")

if __name__ == "__main__":
    print("🔄 STARTING AUTOMATIC CATALOG UPDATE & EXPORT")
    
    # Run all scrapers if no args, or specific ones?
    # For full update:
    run_script("KAVE HOME", "extract_kave_fixed.py")
    run_script("SKLUM", "extract_sklum_v2.py")
    run_script("CASA THAI", "extract_casathai_full.py")
    
    consolidate_data()
