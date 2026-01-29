import sys
import os
import pandas as pd
from sqlalchemy import text, inspect
from sqlalchemy.orm import Session
import logging

# Add parent directory to path to import core modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import SessionLocal, engine
from core.models import Supplier

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def slugify(text):
    return text.lower().replace(" ", "-").replace(".", "").replace("&", "and")

def migrate_schema():
    """Check and add new columns if they don't exist"""
    inspector = inspect(engine)
    columns = [c['name'] for c in inspector.get_columns('suppliers')]
    
    with engine.connect() as conn:
        # Check for all columns that might be missing from legacy DB
        missing_updates = [
            ("fiscal_name", "VARCHAR"),
            ("cif", "VARCHAR"),
            ("address", "VARCHAR"),
            ("city", "VARCHAR"),
            ("zip_code", "VARCHAR"),
            ("country", "VARCHAR DEFAULT 'España'"),
            ("contact_name", "VARCHAR"),
            ("email", "VARCHAR"),
            ("phone", "VARCHAR"),
            ("website", "VARCHAR"),
            ("score", "FLOAT DEFAULT 0.0"),
            ("average_delivery_time", "INTEGER DEFAULT 7"),
            ("payment_terms", "VARCHAR"),
            ("login_url", "VARCHAR"),
            ("credentials_json", "JSON"),
            ("margin_multiplier", "FLOAT DEFAULT 1.56"),
            ("is_active", "BOOLEAN DEFAULT 1"), # SQLite boolean is 1/0
            ("category", "VARCHAR DEFAULT 'General'"),
            ("status", "VARCHAR DEFAULT 'prospect'"),
            ("notes", "TEXT")
        ]

        for col_name, col_type in missing_updates:
            if col_name not in columns:
                logger.info(f"Adding '{col_name}' column...")
                # SQLite doesn't support adding multiple columns in one statement easily or specific positions, 
                # but does support ADD COLUMN.
                try:
                    conn.execute(text(f"ALTER TABLE suppliers ADD COLUMN {col_name} {col_type}"))
                except Exception as e:
                    logger.warning(f"Could not add column {col_name}: {e}")
        
        conn.commit()
    logger.info("Schema migration checked.")

def ingest_csv(csv_path):
    session = SessionLocal()
    try:
        df = pd.read_csv(csv_path)
        logger.info(f"Loaded {len(df)} suppliers from CSV.")
        
        for _, row in df.iterrows():
            name = row['Company']
            code = slugify(name)
            
            # Check if exists
            supplier = session.query(Supplier).filter(Supplier.code == code).first()
            
            if not supplier:
                logger.info(f"Creating new supplier: {name}")
                supplier = Supplier(
                    code=code,
                    name=name,
                    fiscal_name=name, # Placeholder
                    website=row['Website'],
                    category=row['Category'], # Mapping CSV 'Category' to model 'category'
                    status="prospect",
                    notes=f"Subcategory: {row['Subcategory']}, Type: {row['Type']}, Notes: {row['Notes']}"
                )
                session.add(supplier)
            else:
                logger.info(f"Updating existing supplier: {name}")
                supplier.category = row['Category']
                supplier.website = row['Website']
                supplier.notes = f"Subcategory: {row['Subcategory']}, Type: {row['Type']}, Notes: {row['Notes']}"
                if not supplier.status:
                     supplier.status = "prospect"
        
        session.commit()
        logger.info("Ingestion completed successfully.")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error during ingestion: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    csv_file = "C:/Users/User/.gemini/antigravity/brain/8746e8c4-c106-4df8-b64a-9869a6ed1a3f/Adquify_Target_Suppliers.csv"
    
    logger.info("Starting migration...")
    migrate_schema()
    
    logger.info("Starting ingestion...")
    if os.path.exists(csv_file):
        ingest_csv(csv_file)
    else:
        logger.error(f"CSV file not found at: {csv_file}")
