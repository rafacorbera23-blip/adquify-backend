import sys
import os

# Add the current directory to path so we can import modules
sys.path.append(os.getcwd())

from core.database import SessionLocal
from core.models import User
from core.security import verify_password, get_password_hash

def test_login():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "admin@adquify.com").first()
        if not user:
            print("ERROR: User not found in DB!")
            return

        print(f"User found: {user.email}")
        print(f"Role: {user.role}")
        print(f"Hashed Password in DB: {user.hashed_password[:10]}...")

        # Test valid password
        password = "AdquifyAdmin2026!"
        params_valid = verify_password(password, user.hashed_password)
        
        if params_valid:
            print("SUCCESS: Password verification passed!")
        else:
            print("FAILURE: Password verification failed.")
            print("Attempting to re-hash and update...")
            
            # Auto-fix if failed
            new_hash = get_password_hash(password)
            user.hashed_password = new_hash
            db.commit()
            print("Password updated in DB. Try logging in again.")

    except Exception as e:
        print(f"Exception: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_login()
