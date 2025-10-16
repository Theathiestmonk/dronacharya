import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

def get_database_url():
    """Get database URL from environment variables."""
    # Try PostgreSQL first
    postgres_url = os.getenv("DATABASE_URL")
    if postgres_url:
        return postgres_url
    
    # Fallback to SQLite for development
    sqlite_url = os.getenv("SQLITE_URL", "sqlite:///./dronacharya.db")
    return sqlite_url

def get_engine():
    """Get database engine."""
    database_url = get_database_url()
    
    if database_url.startswith("sqlite"):
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False}
        )
    else:
        engine = create_engine(database_url)
    
    return engine

def get_session_local():
    """Get database session factory."""
    engine = get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create session factory
SessionLocal = get_session_local()

def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()




