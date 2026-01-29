from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    PROJECT_NAME: str = "Adquify Engine"
    
    # Path Configuration
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    
    # Database (Default to SQLite for immediate functionality, easy switch to Postgres)
    DATABASE_URL: str = f"sqlite:///{DATA_DIR}/adquify_core.db"
    
    # Security / Suppliers
    SECRET_KEY: str = "supersecretkey"  # Change in prod!

settings = Settings()
