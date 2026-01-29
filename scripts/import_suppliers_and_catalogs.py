
import os
import sys
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import SessionLocal, engine
from core.models import Base, Supplier


# Config
CSV_PATH = r"C:\Treball\1.Negocios\Adquify\GPAContract\Proveedores\Proveedores(Hoja1).csv"
SUPPLIERS_ROOT_DIR = r"C:\Treball\1.Negocios\Adquify\GPAContract\Proveedores"
REPORTS_DIR = r"C:\Treball\1.Negocios\Adquify\adquify-engine\reports"

# Ensure reports dir exists
os.makedirs(REPORTS_DIR, exist_ok=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def parse_csv_data():
    """
    Returns a list of dicts with raw CSV data.
    Attempts to read line by line if pandas fails to parse correctly.
    """
    data = []
    try:
        # Regex approach for this messy file
        # It seems lines are like: ID;Name;Cif;...
        import re
        with open(CSV_PATH, 'r', encoding='latin-1', errors='replace') as f:
            for line in f:
                parts = line.split(';')
                if len(parts) > 2:
                    # Heuristic: 2nd or 3rd column is usually name
                    # Example: 1;MOPAL TAPIZADOS SL;B73373227;...
                    entry = {
                        'raw': line,
                        'name': parts[1].strip() if len(parts) > 1 else "",
                        'cif': parts[2].strip() if len(parts) > 2 else "",
                        'email': ""
                    }
                    # Extract email with regex
                    emails = re.findall(r'[\w\.-]+@[\w\.-]+', line)
                    if emails:
                        entry['email'] = emails[0]
                    
                    data.append(entry)
    except Exception as e:
        print(f"Error parsing CSV: {e}")
    return data

def find_csv_info(supplier_name, csv_data):
    """
    Fuzzy find supplier in parsed CSV data
    """
    normalized_name = supplier_name.lower().replace(" ", "")
    for entry in csv_data:
        csv_name = entry['name'].lower().replace(" ", "")
        if normalized_name in csv_name or csv_name in normalized_name:
            return entry
    return None

def scan_catalog_status(directory):
    if not directory or not os.path.exists(directory):
        return "No Folder Found", []
        
    files = []
    catalog_found = False
    price_list_found = False
    
    for root, dirs, filenames in os.walk(directory):
        for f in filenames:
            lower_f = f.lower()
            if lower_f.endswith(('.xlsx', '.xls', '.csv', '.pdf')):
                files.append(f)
                if any(x in lower_f for x in ['precio', 'price', 'pvp', 'tarifa', 'cost']):
                    price_list_found = True
                if any(x in lower_f for x in ['catalogo', 'catalog', 'productos', 'collection']):
                    catalog_found = True
                    
    status = "Folder Empty"
    if files:
        if price_list_found:
            status = "Price List Found"
        elif catalog_found:
            status = "Catalog Found (No Price List Detected)"
        else:
            status = "Files Present (Unclassified)"
            
    return status, files

def clean_supplier_name(dir_name):
    # Remove parens like "Name (contact)"
    if '(' in dir_name:
        return dir_name.split('(')[0].strip()
    return dir_name.strip()

def main():
    print("Starting Supplier Import (Folder-based)...")
    
    csv_data = parse_csv_data()
    print(f"Loaded {len(csv_data)} potential CSV entries for lookup.")

    db = SessionLocal()
    
    report_lines = ["# Supplier Import Report", f"Date: {datetime.now()}", "", "| Supplier | Source Folder | Status | Files Found | Email Found |", "|---|---|---|---|---|"]
    email_drafts = ["# Draft Outreach Emails"]
    
    total_processed = 0
    
    # Iterate directories
    ignored_dirs = ['.dtrash', '.mysql.digikam']
    
    for item in os.listdir(SUPPLIERS_ROOT_DIR):
        full_path = os.path.join(SUPPLIERS_ROOT_DIR, item)
        if not os.path.isdir(full_path) or item in ignored_dirs:
            continue
            
        print(f"Processing folder: {item}")
        original_name = item
        clean_name = clean_supplier_name(item)
        
        # Check CSV info
        csv_info = find_csv_info(clean_name, csv_data)
        
        # Create or Update Supplier
        supplier = db.query(Supplier).filter(Supplier.name == clean_name).first()
        if not supplier:
            supplier = Supplier(name=clean_name)
            db.add(supplier)
            db.commit()
            db.refresh(supplier)
            
        # Update info if valid
        if csv_info:
            if csv_info['cif'] and len(csv_info['cif']) > 5:
                supplier.cif = csv_info['cif']
            if csv_info['email']:
                supplier.email = csv_info['email']
        
        # Folder Scan
        folder_status, files = scan_catalog_status(full_path)
        
        supplier.notes = f"Imported from Folder '{original_name}'. Status: {folder_status}"
        
        db.add(supplier)
        
        # Report
        file_list_str = ", ".join(files[:3]) + ("..." if len(files) > 3 else "")
        email_str = supplier.email if supplier.email else "MISSING"
        report_lines.append(f"| {clean_name} | {original_name} | {folder_status} | {file_list_str} | {email_str} |")
        
        # Email Draft (if missing info)
        # Draft if empty folder OR no email (though we can't send it, we list it)
        if folder_status in ["No Folder Found", "Folder Empty", "Files Present (Unclassified)"]:
            email_drafts.append(f"## {clean_name}")
            email_drafts.append(f"**To:** {email_str}")
            email_drafts.append(f"**Subject:** Solicitud de Catálogo y Tarifas - Adquify - {clean_name}")
            email_drafts.append("")
            email_drafts.append(f"Hola equipo de {clean_name},")
            email_drafts.append("")
            email_drafts.append(f"Estamos actualizando nuestra base de datos de proveedores en Adquify.")
            if folder_status == "Files Present (Unclassified)":
                email_drafts.append("Hemos encontrado algunos archivos, pero no identificamos claramente una tarifa de precios vigente.")
            else:
                email_drafts.append("No hemos encontrado catálogos ni tarifas actualizadas.")
            email_drafts.append("")
            email_drafts.append("¿Podríais enviarnos la información actualizada?")
            email_drafts.append("")
            email_drafts.append("---")
            
        total_processed += 1
        
    db.commit()
    db.close()
    
    # Save Artifacts
    with open(os.path.join(REPORTS_DIR, "import_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        
    with open(os.path.join(REPORTS_DIR, "email_drafts.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(email_drafts))
        
    print(f"Processed {total_processed} suppliers.")
    print(f"Reports saved to {REPORTS_DIR}")

if __name__ == "__main__":
    main()

