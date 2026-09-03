from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# For local testing. Swap with your Supabase/Postgres URL later: 
# SQLALCHEMY_DATABASE_URL = "postgresql://user:password@localhost/dbname"
SQLALCHEMY_DATABASE_URL = "sqlite:///./ksu_lms.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False} # Only needed for SQLite
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to inject into your routers
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()