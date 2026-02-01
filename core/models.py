from sqlalchemy import Column, Integer, String, Float, Boolean, JSON, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String, nullable=True)
    company_name = Column(String, nullable=True)
    role = Column(String, default="customer") # admin, customer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Supplier(Base):
    __tablename__ = "suppliers"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)  # 'distrigal', 'kave', 'sklum'
    name = Column(String)
    integration_type = Column(String, default="scraping") # API, CSV, SCRAPING

    
    # Fiscal Data
    fiscal_name = Column(String, nullable=True)
    cif = Column(String, nullable=True)
    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)
    country = Column(String, default="España")
    
    # Contact Info
    contact_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    website = Column(String, nullable=True)
    
    # Business Data
    score = Column(Float, default=0.0)
    average_delivery_time = Column(Integer, default=7) # Days
    payment_terms = Column(String, nullable=True) # e.g. "Net 30"
    
    # Classification
    category = Column(String, index=True, default="General") # OS&E, FF&E, etc.
    status = Column(String, default="prospect") # active, prospect, pending
    notes = Column(Text, nullable=True)
    
    # Technical
    login_url = Column(String, nullable=True)
    credentials_json = Column(JSON, default={}) # Encrypted in real app
    margin_multiplier = Column(Float, default=1.56)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    products = relationship("Product", back_populates="supplier")
    orders = relationship("Order", back_populates="supplier")

class Client(Base):
    __tablename__ = "clients"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True) # Hotel Name / Business Name
    fiscal_name = Column(String, nullable=True)
    cif = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)
    
    orders = relationship("Order", back_populates="client")

class Agent(Base):
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, nullable=True)
    commission_percent = Column(Float, default=0.10) # 10% default
    total_sales = Column(Float, default=0.0)
    
    orders = relationship("Order", back_populates="agent")

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String, unique=True, index=True)
    status = Column(String, default="draft") # draft, confirmed, shipped, delivered, cancelled
    total_amount = Column(Float, default=0.0)
    date = Column(DateTime, default=datetime.utcnow)
    
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    supplier = relationship("Supplier", back_populates="orders")
    
    
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    client = relationship("Client", back_populates="orders")
    
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    agent = relationship("Agent", back_populates="orders")
    
    invoices = relationship("Invoice", back_populates="order")

class Invoice(Base):
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String, unique=True)
    date = Column(DateTime, default=datetime.utcnow)
    amount = Column(Float)
    file_path = Column(String, nullable=True) # Path to PDF
    
    order_id = Column(Integer, ForeignKey("orders.id"))
    order = relationship("Order", back_populates="invoices")

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    sku_adquify = Column(String, unique=True, index=True)  # ADQ-1234
    sku_supplier = Column(String, index=True) 
    
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    supplier = relationship("Supplier", back_populates="products")
    
    # Core Data
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    category = Column(String, index=True)
    
    # Pricing
    cost_price = Column(Float) # Precio Coste
    selling_price = Column(Float) # PVP Adquify
    
    # Inventory
    stock_actual = Column(Integer, default=0)
    status_stock = Column(String, default="red") # green, yellow, red
    last_sync = Column(DateTime, default=datetime.utcnow)
    
    # Metadata
    metadata_json = Column(JSON, default={}) # Dimensions, colors, weights
    raw_data = Column(JSON, default={}) # Original raw data from scraping
    status = Column(String, default="draft") # draft, reviewed, published
    
    # Embedding Cache (for fast re-indexing)
    embedding_json = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    images = relationship("ProductImage", back_populates="product")

class ProductImage(Base):
    __tablename__ = "product_images"
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    product = relationship("Product", back_populates="images")
    
    url = Column(String)
    local_path = Column(String, nullable=True)
    
    # Vector Embedding for Visual Search (stored as JSON/Array for SQLite loop compat)
    # in Postgres/pgvector this would be Vector(512)
    embedding_json = Column(JSON, nullable=True) 
