from core.database import SessionLocal, engine, Base
from core.models import User
from core.security import get_password_hash
import logging

# Ensure tables exist
Base.metadata.create_all(bind=engine)

def create_admin_user():
    db = SessionLocal()
    try:
        email = "admin@adquify.com"
        password = "AdquifyAdmin2026!"
        
        user = db.query(User).filter(User.email == email).first()
        
        if user:
            print(f"User {email} found. Resetting password...")
            user.hashed_password = get_password_hash(password)
            user.role = "admin"
            user.full_name = "Admin Adquify"
        else:
            print(f"Creating new admin user {email}...")
            user = User(
                email=email,
                hashed_password=get_password_hash(password),
                full_name="Admin Adquify",
                role="admin",
                company_name="Adquify HQ"
            )
            db.add(user)
        
        db.commit()
        print(f"SUCCESS: Admin user ready.")
        print(f"Email: {email}")
        print(f"Password: {password}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_admin_user()
