"""
Adquify Engine - API Backend Funcional
========================================
API completa para gestión de scrapers, credenciales y catálogo interno.
"""

# Load Env Vars FIRST
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import json
import os
import asyncio
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from core.database import get_db, SessionLocal
from core.models import Product, Supplier, ProductImage
from services.chat_engine import AdquifyChatEngine
from core.ai.vector_store import QdrantHandler
from services.sync_service import reindex_qdrant_from_db, generate_missing_embeddings
from departments.procurement.scraping_skill.scripts.catalog_merger import CatalogMergerAgent
from fastapi import BackgroundTasks, Depends

# Ensure Tables & Migrations
from core.database import engine, Base
from sqlalchemy import inspect, text

def run_migrations():
    """Simple startup migration to fix schema drift in SQLite"""
    try:
        inspector = inspect(engine)
        if "products" in inspector.get_table_names():
            columns = [c["name"] for c in inspector.get_columns("products")]
            
            with engine.connect() as conn:
                # 1. stock_quantity
                if "stock_quantity" not in columns:
                    print("⚠️ Migration: Adding 'stock_quantity' column...")
                    conn.execute(text("ALTER TABLE products ADD COLUMN stock_quantity INTEGER DEFAULT 0"))
                
                # 2. last_stock_update
                if "last_stock_update" not in columns:
                    print("⚠️ Migration: Adding 'last_stock_update' column...")
                    conn.execute(text("ALTER TABLE products ADD COLUMN last_stock_update TIMESTAMP"))
                
                conn.commit()
            print("✅ DB Migrations Checked.")
    except Exception as e:
        print(f"❌ Migration Error: {e}")

run_migrations()
Base.metadata.create_all(bind=engine)

# Paths
ENGINE_ROOT = Path(__file__).parent.parent
CONFIG_PATH = ENGINE_ROOT / "config" / "suppliers_credentials.json"
DATA_RAW = ENGINE_ROOT / "data" / "raw"
ASSETS_IMAGES = ENGINE_ROOT / "assets" / "images"

# Asegurar directorios
DATA_RAW.mkdir(parents=True, exist_ok=True)
ASSETS_IMAGES.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Adquify Engine API",
    description="Motor de scraping y gestión de catálogo",
    version="1.0.0"
)

# Include Auth Router
from api.routers import auth
app.include_router(auth.router)

# Include Scheduler Router
from api.routers import scheduler
app.include_router(scheduler.router)

# Include Voice Router
from api.routers import voice
app.include_router(voice.router)

# Include Suppliers V2 Router
from api.routers import suppliers_v2
app.include_router(suppliers_v2.router)

# Include Innovation Router
from api.routers import innovation_v1
app.include_router(innovation_v1.router)

# Include WhatsApp Router
from api.routers import whatsapp
app.include_router(whatsapp.router)

# Startup/Shutdown Events
from contextlib import asynccontextmanager
from services.scheduler_service import get_scheduler
from services.notification_service import get_notification_service

@app.on_event("startup")
async def startup_event():
    """Initialize scheduler and AI services on startup"""
    scheduler = get_scheduler()
    scheduler.start()
    
    # Initialize Global Qdrant Handler (Singleton for :memory: persistence)
    try:
        app.state.qdrant_handler = QdrantHandler()
        app.state.qdrant_handler.ensure_collection()
        print("✅ Qdrant Handler Initialized")
        
        # Trigger Re-indexing from DB (Background)
        # We need a dedicated DB session for this background task that closes afterwards
        async def run_reindex():
            db = SessionLocal()
            try:
                await reindex_qdrant_from_db(db, app.state.qdrant_handler)
            finally:
                db.close()
                
        asyncio.create_task(run_reindex())
        print("🚀 Background Re-indexing Task Started")
        
    except Exception as e:
        print(f"❌ Failed to initialize Qdrant: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    scheduler = get_scheduler()
    scheduler.stop()
    notif = get_notification_service()
    await notif.close()

from dotenv import load_dotenv
load_dotenv()

# Ensure Tables Exist
from core.database import engine, Base
from sqlalchemy import inspect, text

def run_migrations():
    """Simple startup migration to fix schema drift in SQLite"""
    inspector = inspect(engine)
    if "products" in inspector.get_table_names():
        columns = [c["name"] for c in inspector.get_columns("products")]
        if "stock_quantity" not in columns:
            print("⚠️ Migration: Adding 'stock_quantity' column to products table...")
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE products ADD COLUMN stock_quantity INTEGER DEFAULT 0"))
                conn.commit()
            print("✅ Migration: 'stock_quantity' added.")

# Run migrations BEFORE creating tables (or after, create_all won't touch existing tables)
run_migrations()
Base.metadata.create_all(bind=engine)

# CORS

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex='.*',
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
app.mount("/files", StaticFiles(directory=ENGINE_ROOT / "data"), name="files")

# ===== MODELOS =====

class CredentialsUpdate(BaseModel):
    supplier_code: str
    email: str
    password: str

class ScraperRunRequest(BaseModel):
    supplier_code: str
    max_pages: int = 5
    dry_run: bool = False

class ProductPublish(BaseModel):
    product_ids: List[str]

class SupplierStatus(BaseModel):
    code: str
    name: str
    status: str
    source: str
    products_count: int
    last_sync: Optional[str]
    margin: float
    has_credentials: bool

# ===== ESTADO GLOBAL =====

scraper_status = {}  # {supplier_code: {status, progress, message}}

# ===== FUNCIONES AUXILIARES =====

def load_config() -> dict:
    """Carga configuración de proveedores"""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"suppliers": {}}

def save_config(config: dict):
    """Guarda configuración"""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def get_internal_products(skip: int = 0, limit: int = 50, q: Optional[str] = None, category: Optional[str] = None) -> List[dict]:
    """Obtiene productos del catálogo interno (SQL Database) con filtros"""
    db: Session = SessionLocal()
    try:
        query = db.query(Product).filter(Product.status == "published")
        
        if q:
            search = f"%{q}%"
            query = query.filter(Product.name.ilike(search) | Product.description.ilike(search))
        
        if category and category != "Todos":
            query = query.filter(Product.category.ilike(f"%{category}%"))

        total = query.count()
        products_orm = query.offset(skip).limit(limit).all()
        
        results = []
        for p in products_orm:
            # Obtener primera imagen o placeholder
            img_url = p.images[0].url if p.images else "https://via.placeholder.com/400"
            
            supplier_code = p.supplier.code if p.supplier else "Unknown"
            
            results.append({
                "id": p.sku_adquify,
                "name": p.name,
                "category": p.category,
                "price": p.selling_price,
                "image": img_url,
                "supplier": supplier_code,
                "stock": p.stock_quantity if p.last_stock_update else "Consultar", # Real stock
                "description": p.description
            })
        return results
    finally:
        db.close()

@app.get("/products")
async def read_products(skip: int = 0, limit: int = 50, q: Optional[str] = None, category: Optional[str] = None):
    return get_internal_products(skip, limit, q, category)



def count_products_by_supplier(supplier_code: str) -> int:
    """Cuenta productos de un proveedor (SQL)"""
    db: Session = SessionLocal()
    try:
        return db.query(Product).join(Supplier).filter(Supplier.code == supplier_code).count()
    except:
        return 0
    finally:
        db.close()

def get_last_sync(supplier_code: str) -> Optional[str]:
    """Obtiene última sincronización de un proveedor"""
    latest = None
    for json_file in DATA_RAW.glob(f"{supplier_code.lower()}*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                extracted = data.get('extracted_at')
                if extracted and (not latest or extracted > latest):
                    latest = extracted
        except:
            pass
    return latest

# ===== ENDPOINTS =====

@app.get("/")
def root():
    return {"status": "ok", "message": "Adquify Engine API", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# ----- PROVEEDORES -----

@app.get("/suppliers", response_model=List[SupplierStatus])
def get_suppliers():
    """Lista todos los proveedores con su estado"""
    config = load_config()
    suppliers = []
    
    for code, data in config.get('suppliers', {}).items():
        creds = data.get('credentials', {})
        has_creds = bool(creds and creds.get('email') and creds.get('password'))
        source = data.get('source', 'web')
        
        # Determinar estado
        if source == 'excel':
            status = 'active'
        elif has_creds:
            status = 'active'
        else:
            status = 'pending'
        
        suppliers.append(SupplierStatus(
            code=code,
            name=data.get('name', code),
            status=status,
            source='Excel' if source == 'excel' else 'Web Scraping',
            products_count=count_products_by_supplier(code),
            last_sync=get_last_sync(code),
            margin=data.get('margin', 0.25),
            has_credentials=has_creds
        ))
    
    return suppliers

@app.get("/suppliers/{supplier_code}")
def get_supplier(supplier_code: str):
    """Obtiene detalles de un proveedor"""
    config = load_config()
    supplier = config.get('suppliers', {}).get(supplier_code)
    
    if not supplier:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    
    # No devolver contraseñas
    result = {**supplier}
    if 'credentials' in result and result['credentials']:
        result['credentials'] = {
            'email': result['credentials'].get('email', ''),
            'has_password': bool(result['credentials'].get('password'))
        }
    
    result['products_count'] = count_products_by_supplier(supplier_code)
    result['last_sync'] = get_last_sync(supplier_code)
    
    return result

# ----- CREDENCIALES -----

@app.post("/credentials")
def update_credentials(creds: CredentialsUpdate):
    """Actualiza credenciales de un proveedor"""
    config = load_config()
    
    if creds.supplier_code not in config.get('suppliers', {}):
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    
    config['suppliers'][creds.supplier_code]['credentials'] = {
        'email': creds.email,
        'password': creds.password
    }
    
    save_config(config)
    
    return {"success": True, "message": f"Credenciales de {creds.supplier_code} actualizadas"}

@app.get("/credentials/{supplier_code}")
def get_credentials(supplier_code: str):
    """Obtiene credenciales (email visible, password oculta)"""
    config = load_config()
    supplier = config.get('suppliers', {}).get(supplier_code)
    
    if not supplier:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    
    creds = supplier.get('credentials', {})
    return {
        'email': creds.get('email', ''),
        'has_password': bool(creds.get('password')),
        'login_url': supplier.get('loginUrl', '')
    }

# ----- SCRAPERS -----

@app.post("/scrapers/run/{supplier_code}")
async def run_scraper(supplier_code: str, background_tasks: BackgroundTasks, max_pages: int = 5):
    """Ejecuta scraper en background"""
    config = load_config()
    supplier = config.get('suppliers', {}).get(supplier_code)
    
    if not supplier:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    
    # Verificar si ya está corriendo
    if scraper_status.get(supplier_code, {}).get('status') == 'running':
        raise HTTPException(status_code=409, detail="Scraper ya en ejecución")
    
    # Iniciar en background
    scraper_status[supplier_code] = {
        'status': 'running',
        'progress': 0,
        'message': 'Iniciando...',
        'started_at': datetime.utcnow().isoformat()
    }
    
    background_tasks.add_task(execute_scraper, supplier_code, max_pages, supplier)
    
    return {"success": True, "message": f"Scraper {supplier_code} iniciado"}

async def execute_scraper(supplier_code: str, max_pages: int, supplier_config: dict):
    """Ejecuta el scraper (función background)"""
    try:
        scraper_status[supplier_code]['message'] = 'Conectando...'
        
        # Importar y ejecutar el scraper apropiado
        if supplier_config.get('source') == 'excel':
            # Scraper de Excel
            scraper_status[supplier_code]['message'] = 'Leyendo Excel...'
            await asyncio.sleep(1)  # Simular tiempo
            
            from departments.procurement.bambo_blau import extract_from_excel, save_raw_json
            products = extract_from_excel()
            if products:
                save_raw_json(products)
            
            scraper_status[supplier_code] = {
                'status': 'completed',
                'progress': 100,
                'message': f'Completado: {len(products)} productos',
                'products_count': len(products),
                'completed_at': datetime.utcnow().isoformat()
            }
        else:
            # Scraper web autenticado (Unified)
            scraper_status[supplier_code]['message'] = 'Iniciando sesión segura...'
            
            # Importar scraper especializado
            if supplier_code == 'KAVE':
                scraper_status[supplier_code]['message'] = 'Conectando a API Catalogo...'
                from departments.procurement.kave_algolia import scrape_kave
                products = await scrape_kave(scraper_status)
                
                # Persistir datos
                if products:
                    try:
                        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                        outfile = DATA_RAW / f"{supplier_code.lower()}_{timestamp}.json"
                        with open(outfile, 'w', encoding='utf-8') as f:
                            json.dump({
                                'supplier': supplier_code,
                                'extracted_at': datetime.utcnow().isoformat(),
                                'count': len(products),
                                'products': products
                            }, f, default=str, ensure_ascii=False)
                        scraper_status[supplier_code]['message'] = f"Guardado en {outfile.name}"
                    except Exception as e:
                        print(f"Error saving JSON: {e}")
            else:
                # Fallback genérico (Sklum, Distrigal, etc)
                from departments.procurement.web_scraper_auth import run_scraper as run_auth_scraper
                products = await run_auth_scraper(supplier_code, scraper_status)
            
            scraper_status[supplier_code] = {
                'status': 'completed',
                'progress': 100,
                'message': f'Completado: {len(products) if products else 0} productos',
                'products_count': len(products) if products else 0,
                'completed_at': datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        scraper_status[supplier_code] = {
            'status': 'error',
            'progress': 0,
            'message': str(e),
            'error': str(e),
            'completed_at': datetime.utcnow().isoformat()
        }

@app.get("/scrapers/status/{supplier_code}")
def get_scraper_status(supplier_code: str):
    """Obtiene estado de un scraper"""
    return scraper_status.get(supplier_code, {
        'status': 'idle',
        'progress': 0,
        'message': 'Sin ejecutar'
    })

@app.get("/scrapers/status")
def get_all_scraper_status():
    """Obtiene estado de todos los scrapers"""
    return scraper_status

# ----- CATÁLOGO INTERNO -----

@app.get("/internal-catalog")
def get_internal_catalog(
    supplier: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """Obtiene productos del catálogo interno"""
    products = get_internal_products()
    
    # Filtrar por proveedor
    if supplier and supplier != 'all':
        products = [p for p in products if p.get('supplier_code') == supplier]
    
    # Añadir estado (simulado por ahora)
    for p in products:
        p['status'] = p.get('status', 'pending')
        p['id'] = p.get('sku_adquify', f"prod-{products.index(p)}")
    
    # Filtrar por estado
    if status and status != 'all':
        products = [p for p in products if p.get('status') == status]
    
    total = len(products)
    products = products[offset:offset + limit]
    
    return {
        'total': total,
        'offset': offset,
        'limit': limit,
        'products': products
    }

@app.post("/internal-catalog/publish")
def publish_products(request: ProductPublish):
    """Publica productos al catálogo digital"""
    products = get_internal_products()
    
    published = []
    for p in products:
        if p.get('sku_adquify') in request.product_ids or p.get('id') in request.product_ids:
            p['status'] = 'published'
            published.append(p.get('sku_adquify'))
    
    # TODO: Guardar cambios de estado
    
    return {
        'success': True,
        'published_count': len(published),
        'published_ids': published
    }

@app.get("/internal-catalog/export/csv")
def export_client_catalog():
    """Generates and returns the path to the CSV catalog"""
    # Import logic dynamically to avoid circular imports if any
    try:
        from core.catalog_processor import AdquifyProcessor
        products = get_internal_products()
        
        processor = AdquifyProcessor(products)
        df_result = processor.process()
        
        # Save to exports
        exports_dir = ENGINE_ROOT / "data" / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        
        filename = "Catalogo_Maestro_Adquify_Interactive_LATEST.csv"
        file_path = exports_dir / filename
        df_result.to_csv(file_path, index=False, encoding='utf-8-sig')
        
        return {
            "success": True,
            "message": "Call Catalog Update generated",
            "file_path": str(file_path),
            "download_url": f"/files/exports/{filename}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ----- VISUAL SEARCH -----

from fastapi import UploadFile, File
# from services.visual_search import VisualSearchService
from io import BytesIO
import numpy as np
from PIL import Image

# Initialize Service (Lazy load in prod, but eager here for demo)
# Global instance
visual_search = None

# Initialize Service (Agent)
# from departments.procurement.visual_search_agent import VisualSearchAgent
# visual_search_agent = VisualSearchAgent()
visual_search_agent = None

def get_visual_search_agent():
    return visual_search_agent

@app.post("/search/image")
async def search_by_image(file: UploadFile = File(...)):
    """Busca productos similares por imagen"""
    # service = get_visual_search()
    
    # 1. Read Image
    content = await file.read()
    # img = Image.open(BytesIO(content)) # Not needed for Agent call yet
    

        
    """Busca productos similares por imagen usando el Agente"""
    agent = get_visual_search_agent()
    
    # 1. Read Image URL or Content
    # For prototype, we might need a way to pass URL or save the file temporarily
    # The agent expects a URL or path currently.
    
    # FIXME: The agent currently expects a URL in the signature: search_by_image(image_url: str)
    # But this endpoint receives bytes.
    # We will wrap it to save to a temp file or just mock the call for now as per the Agent's design.
    
    # Save to temp file
    temp_filename = f"temp_search_{file.filename}"
    temp_path = DATA_RAW / temp_filename
    with open(temp_path, "wb") as buffer:
        buffer.write(content)
        
        # Call Agent
        # We pass the file path as "url" for now
        results = agent.search_by_image(str(temp_path))
        
        return results


# ----- SCRAPEMASTER -----

class ScrapeMasterRequest(BaseModel):
    url: str
    username: Optional[str] = None
    password: Optional[str] = None

@app.post("/scrapemaster/analyze")
async def scrapemaster_analyze(req: ScrapeMasterRequest):
    """
    Generic scraper endpoint (ScrapeMaster AI)
    """
    try:
        # Import lazily to avoid circular deps if any
        from departments.procurement.generic_scraper import run_analysis
        
        # Run synchronous or wait? 
        # For a "Tool", the user probably waits or we utilize background tasks if long running.
        # Given "run_analysis" is async, we can await it.
        # Timeout might be an issue for long scrapes. 
        # Ideally this should be a background task, but for a simple "Preview" tool, let's await.
        # User asked for "export everything", which implies long running.
        # But for UX "functional", immediate feedback is good.
        # Let's await it for now (Playwright takes time though).
        # We'll set a reasonable limit in the scraper (max pages).
        
        result = await run_analysis(req.url, req.username, req.password)
        return result
    except Exception as e:
        print(f"ScrapeMaster Error: {e}")
        return {"success": False, "message": str(e)}

# ----- ESTADÍSTICAS -----

@app.get("/stats")
def get_stats():
    """Obtiene estadísticas generales"""
    config = load_config()
    products = get_internal_products()
    
    suppliers = list(config.get('suppliers', {}).keys())
    active_suppliers = sum(1 for s in suppliers if count_products_by_supplier(s) > 0)
    
    return {
        'total_products': len(products),
        'total_suppliers': len(suppliers),
        'active_scrapers': active_suppliers,
        'pending_products': len([p for p in products if p.get('status') != 'published']),
        'published_products': len([p for p in products if p.get('status') == 'published']),
        'last_sync': max([get_last_sync(s) for s in suppliers if get_last_sync(s)], default=None),
        'images_stored': len(list(ASSETS_IMAGES.glob('**/*.*')))
    }


# ----- SMART CHAT -----

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat_with_catalog(req: ChatRequest):
    """Interfaz de chat inteligente con el catálogo"""
    db: Session = SessionLocal()
    try:
        # Use Singleton Qdrant Handler if available (crucial for :memory: mode)
        qdrant_handler = getattr(app.state, "qdrant_handler", None)
        
        engine = AdquifyChatEngine(db, vector_store=qdrant_handler)
        response = await engine.process_query(req.message)
        return response
    finally:
        db.close()

# ===== MAIN =====


# ===== INGESTION TRIGGER =====

@app.post("/api/ingest/trigger")
async def trigger_ingestion(background_tasks: BackgroundTasks):
    """
    Emergency Trigger: Ingest final_catalog.csv and Reindex Qdrant.
    Request by user to fix empty production DB.
    """
    csv_path = "final_catalog.csv"
    if not os.path.exists(csv_path):
         # Try absolute path fallback
         csv_path = str(Path(os.getcwd()) / "final_catalog.csv")
    
    if not os.path.exists(csv_path):
        # Fallback to checking parent dir if running from api folder
        csv_path = str(Path(__file__).parent.parent / "final_catalog.csv")
        
    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail=f"final_catalog.csv not found in {os.getcwd()} or parent")

    async def _heavy_lifting():
        print(f"🚀 Starting Ingestion from {csv_path}")
        
        # 1. Ingest via Agent (SQLite Population)
        try:
             merger = CatalogMergerAgent()
             merger.merge_and_publish(csv_path)
             print("✅ [Background] SQL Ingestion Complete.")
        except Exception as e:
             print(f"❌ [Background] SQL Ingestion Failed: {e}")
             return

        # 2. Generate Embeddings & Reindex Qdrant
        try:
            db_session = SessionLocal() 
            
            # A. Generate Missing Embeddings (Gemini)
            # This is CRUCIAL for search to work
            await generate_missing_embeddings(db_session)
            
            # B. Push to Qdrant
            # Need strict re-initialization
            q_handler = QdrantHandler()
            
            # Double check connection
            if not q_handler.client:
                print("❌ [Background] Qdrant Client failed to init.")
            else:
                await reindex_qdrant_from_db(db_session, q_handler)
                print("✅ [Background] Qdrant Sync Complete.")
            
            db_session.close()
        except Exception as e:
            print(f"❌ [Background] Sync Failed: {e}")

    background_tasks.add_task(_heavy_lifting)
    return {"status": "Ingestion & Sync started in background", "target_file": csv_path}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)
