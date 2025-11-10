from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# SQLite database
SQLALCHEMY_DATABASE_URL = "sqlite:///./credentials.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def init_db():
    """Initialize database tables"""
    from models import Domain, Credential
    from sqlalchemy import inspect, text
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Add is_checked column to domains if it doesn't exist
    inspector = inspect(engine)
    domain_columns = [col['name'] for col in inspector.get_columns('domains')] if inspector.has_table('domains') else []
    if 'is_checked' not in domain_columns:
        try:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE domains ADD COLUMN is_checked BOOLEAN DEFAULT 0"))
        except Exception as e:
            # Column might already exist or error, ignore
            pass
    
    # Add is_checked column to credentials if it doesn't exist
    cred_columns = [col['name'] for col in inspector.get_columns('credentials')] if inspector.has_table('credentials') else []
    if 'is_checked' not in cred_columns:
        try:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE credentials ADD COLUMN is_checked BOOLEAN DEFAULT 0"))
        except Exception as e:
            # Column might already exist or error, ignore
            pass

def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

