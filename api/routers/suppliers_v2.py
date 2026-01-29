from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from core.database import get_db
from core.models import Supplier, Product, Order, Invoice, Client

router = APIRouter(
    prefix="/api/suppliers/v2",
    tags=["suppliers-v2"]
)

# --- Pydantic Models ---

class SupplierUpdate(BaseModel):
    fiscal_name: Optional[str] = None
    cif: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    score: Optional[float] = None
    average_delivery_time: Optional[int] = None
    payment_terms: Optional[str] = None

class SupplierResponse(BaseModel):
    id: int
    code: str
    name: str
    fiscal_name: Optional[str]
    cif: Optional[str]
    address: Optional[str]
    city: Optional[str]
    zip_code: Optional[str]
    country: Optional[str]
    contact_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    website: Optional[str]
    score: float
    average_delivery_time: int
    payment_terms: Optional[str]
    category: Optional[str]
    status: Optional[str]
    notes: Optional[str]
    products_count: int
    orders_count: int

    class Config:
        orm_mode = True

class OrderResponse(BaseModel):
    id: int
    order_number: str
    status: str
    total_amount: float
    date: datetime
    client_name: Optional[str]
    invoice_number: Optional[str]

# --- Endpoints ---

@router.get("/", response_model=List[SupplierResponse])
def get_all_suppliers(db: Session = Depends(get_db)):
    """Get all suppliers"""
    suppliers = db.query(Supplier).all()
    # We need to compute counts for each (n+1 problem, but fine for MVP)
    results = []
    for s in suppliers:
        p_count = db.query(Product).filter(Product.supplier_id == s.id).count()
        o_count = db.query(Order).filter(Order.supplier_id == s.id).count()
        
        # Safe conversion avoiding _sa_instance_state
        s_data = {
            "id": s.id,
            "code": s.code or f"SUP-{s.id}", # Fallback if code is missing
            "name": s.name,
            "fiscal_name": s.fiscal_name,
            "cif": s.cif,
            "address": s.address,
            "city": s.city,
            "zip_code": s.zip_code,
            "country": s.country,
            "contact_name": s.contact_name,
            "email": s.email,
            "phone": s.phone,
            "website": s.website,
            "score": s.score,
            "average_delivery_time": s.average_delivery_time,
            "payment_terms": s.payment_terms,
            "category": s.category,
            "status": s.status,
            "notes": s.notes,
            "products_count": p_count,
            "orders_count": o_count
        }
        results.append(SupplierResponse(**s_data))
    
    return results

@router.get("/{supplier_id}", response_model=SupplierResponse)
def get_supplier_details(supplier_id: int, db: Session = Depends(get_db)):
    """Get full details for a specific supplier"""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    # Calculate counts dynamically
    products_count = db.query(Product).filter(Product.supplier_id == supplier_id).count()
    orders_count = db.query(Order).filter(Order.supplier_id == supplier_id).count()
    
    # Map to response (Pydanticorm_mode handles the direct fields, we add the counts)
    s_data = {
        "id": supplier.id,
        "code": supplier.code or f"SUP-{supplier.id}",
        "name": supplier.name,
        "fiscal_name": supplier.fiscal_name,
        "cif": supplier.cif,
        "address": supplier.address,
        "city": supplier.city,
        "zip_code": supplier.zip_code,
        "country": supplier.country,
        "contact_name": supplier.contact_name,
        "email": supplier.email,
        "phone": supplier.phone,
        "website": supplier.website,
        "score": supplier.score,
        "average_delivery_time": supplier.average_delivery_time,
        "payment_terms": supplier.payment_terms,
        "category": supplier.category,
        "status": supplier.status,
        "notes": supplier.notes,
        "products_count": products_count,
        "orders_count": orders_count
    }
    response = SupplierResponse(**s_data)
    return response

@router.put("/{supplier_id}")
def update_supplier_details(supplier_id: int, update_data: SupplierUpdate, db: Session = Depends(get_db)):
    """Update supplier details"""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    for key, value in update_data.dict(exclude_unset=True).items():
        setattr(supplier, key, value)
    
    db.commit()
    db.refresh(supplier)
    return supplier

@router.get("/{supplier_id}/orders", response_model=List[OrderResponse])
def get_supplier_orders(supplier_id: int, db: Session = Depends(get_db)):
    """Get purchase history for this supplier"""
    orders = db.query(Order).options(joinedload(Order.client), joinedload(Order.invoices)).filter(Order.supplier_id == supplier_id).all()
    
    result = []
    for o in orders:
        invoice_num = o.invoices[0].invoice_number if o.invoices else None
        client_val = o.client.name if o.client else "Unknown Client"
        
        result.append(OrderResponse(
            id=o.id,
            order_number=o.order_number,
            status=o.status,
            total_amount=o.total_amount,
            date=o.date,
            client_name=client_val,
            invoice_number=invoice_num
        ))
    return result

@router.get("/{supplier_id}/catalog") # Simplified simplified catalog view
def get_supplier_catalog(supplier_id: int, db: Session = Depends(get_db)):
    """Get products for this supplier"""
    products = db.query(Product).options(joinedload(Product.images)).filter(Product.supplier_id == supplier_id).limit(100).all()
    return products

@router.post("/{supplier_id}/mock-seed")
def seed_mock_data(supplier_id: int, db: Session = Depends(get_db)):
    """Seed some mock orders for demo purposes"""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    # Ensure a client exists
    client = db.query(Client).first()
    if not client:
        client = Client(name="Grand Hotel Central", fiscal_name="GHC S.L.", cif="B12345678", contact_email="ghc@example.com")
        db.add(client)
        db.commit()
        db.refresh(client)
        
    # Create orders
    import random
    for i in range(5):
        order = Order(
            order_number=f"ORD-{supplier.code}-{random.randint(1000, 9999)}",
            status=random.choice(["draft", "confirmed", "shipped", "delivered"]),
            total_amount=random.uniform(500, 5000),
            date=datetime.utcnow(),
            supplier_id=supplier.id,
            client_id=client.id
        )
        db.add(order)
    
    db.commit()
    return {"message": "Mock data seeded"}
