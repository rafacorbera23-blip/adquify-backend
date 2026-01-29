"""
Adquify Engine - Database Schema
================================
Esquema SQLAlchemy para productos con soporte de embeddings vectoriales.
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class Supplier(Base):
    """Proveedor/Fuente de productos"""
    __tablename__ = 'suppliers'
    
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)  # ej: "BAMBO", "KAVE", "SKLUM"
    name = Column(String(200), nullable=False)
    website = Column(String(500))
    scraper_enabled = Column(Boolean, default=True)
    last_sync = Column(DateTime)
    
    products = relationship("Product", back_populates="supplier")

class Product(Base):
    """Producto del catálogo"""
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    
    # Identificadores
    sku_adquify = Column(String(50), unique=True, nullable=False)  # SKU interno Adquify
    sku_supplier = Column(String(100))  # SKU del proveedor original
    supplier_id = Column(Integer, ForeignKey('suppliers.id'))
    
    # Información básica
    name_original = Column(String(500))  # Nombre original del proveedor
    name_commercial = Column(String(500))  # Nombre comercial Adquify
    description = Column(Text)
    category = Column(String(200))
    subcategory = Column(String(200))
    
    # Precios
    price_supplier = Column(Float)  # PVP proveedor
    price_adquify = Column(Float)   # PVP Adquify (con margen)
    margin = Column(Float, default=0.25)
    
    # Dimensiones
    dimensions = Column(String(200))  # ej: "120x80x45 cm"
    weight = Column(Float)
    
    # Stock
    stock_available = Column(Boolean, default=True)
    stock_quantity = Column(Integer)
    lead_time_days = Column(Integer)
    
    # Render/IA
    render_prompt = Column(Text)  # Prompt para generación IA
    materials = Column(JSON)      # Lista de materiales detectados
    colors = Column(JSON)         # Colores principales
    style = Column(String(100))   # Estilo: moderno, clásico, industrial...
    
    # Metadatos
    url_source = Column(String(1000))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relaciones
    supplier = relationship("Supplier", back_populates="products")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")

class ProductImage(Base):
    """Imágenes de producto con embeddings para búsqueda visual"""
    __tablename__ = 'product_images'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'))
    
    # Rutas
    url_original = Column(String(1000))  # URL de origen
    path_local = Column(String(500))     # Ruta local en /assets/images
    path_thumbnail = Column(String(500))
    
    # Embedding para búsqueda visual (almacenado como JSON array)
    embedding = Column(JSON)  # Vector de 512/768 dimensiones (CLIP)
    embedding_model = Column(String(100), default="clip-vit-base-patch32")
    
    # Metadatos
    is_primary = Column(Boolean, default=False)
    width = Column(Integer)
    height = Column(Integer)
    
    product = relationship("Product", back_populates="images")

class ScrapeLog(Base):
    """Log de ejecuciones de scraping"""
    __tablename__ = 'scrape_logs'
    
    id = Column(Integer, primary_key=True)
    supplier_code = Column(String(50))
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    status = Column(String(50))  # running, completed, failed
    products_found = Column(Integer, default=0)
    products_new = Column(Integer, default=0)
    products_updated = Column(Integer, default=0)
    products_duplicates = Column(Integer, default=0)
    errors = Column(Text)


# Database setup
DATABASE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'adquify.db')

def get_engine():
    return create_engine(f'sqlite:///{DATABASE_PATH}', echo=False)

def init_db():
    """Inicializa la base de datos"""
    engine = get_engine()
    Base.metadata.create_all(engine)
    print(f"✅ Base de datos inicializada en: {DATABASE_PATH}")
    return engine

def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


if __name__ == "__main__":
    init_db()
