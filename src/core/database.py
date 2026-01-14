from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config.settings import DATABASE_URL

# Use database URL from config
SQLALCHEMY_DATABASE_URL = DATABASE_URL

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def init_db():
    """Initialize database tables"""
    from src.core.models import Domain, Credential, User, UserRole, DomainAssignment, CredentialStatus
    from sqlalchemy import inspect, text
    from src.core.auth import get_password_hash
    
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
    
    # Add status_id column to credentials if it doesn't exist
    if 'status_id' not in cred_columns:
        try:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE credentials ADD COLUMN status_id INTEGER"))
        except Exception as e:
            pass
    
    # Add comment column to domains if it doesn't exist
    if 'comment' not in domain_columns:
        try:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE domains ADD COLUMN comment VARCHAR"))
        except Exception as e:
            pass
    
    # Create default admin user if it doesn't exist
    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            admin_user = User(
                username="admin",
                password_hash=get_password_hash("admin123"),  # Change this password!
                role=UserRole.ADMIN,
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            print("Default admin user created: username='admin', password='admin123'")
            print("⚠️  IMPORTANT: Change the admin password immediately!")
        
        # Create default status options if they don't exist
        default_statuses = [
            ("Active", "Active credentials", "#10b981"),
            ("Inactive", "Inactive credentials", "#ef4444"),
            ("Pending", "Pending verification", "#f59e0b"),
            ("Expired", "Expired credentials", "#6b7280")
        ]
        
        for name, desc, color in default_statuses:
            status = db.query(CredentialStatus).filter(CredentialStatus.name == name).first()
            if not status:
                status = CredentialStatus(
                    name=name,
                    description=desc,
                    color=color,
                    is_active=True
                )
                db.add(status)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error initializing default data: {e}")
    finally:
        db.close()

def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

