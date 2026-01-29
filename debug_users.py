from core.database import SessionLocal
from core.models import User

def list_users():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print(f"Total Users: {len(users)}")
        print("-" * 50)
        for u in users:
            print(f"ID: {u.id} | Email: {u.email} | Role: {u.role}")
            print(f"Hash Start: {u.hashed_password[:20] if u.hashed_password else 'None'}")
            print("-" * 50)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    list_users()
