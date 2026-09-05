import os
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Load .env variables
load_dotenv()

logger = logging.getLogger(__name__)

# Default to local SQLite fallback if PostgreSQL is not specified or unavailable
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    POSTGRES_USER = os.getenv("POSTGRES_USER", "pms_user")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "pms_secret")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "pms_db")
    DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Attempt to create engine, fallback gracefully to SQLite if PostgreSQL connection fails
try:
    if DATABASE_URL.startswith("postgresql"):
        # Configure robust connection pooling for high-concurrency production workloads
        test_engine = create_engine(
            DATABASE_URL,
            connect_args={'connect_timeout': 5},
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=300,
            pool_pre_ping=True
        )
        with test_engine.connect() as conn:
            pass
        engine = test_engine
        print(f"Connected to PostgreSQL database: {DATABASE_URL.split('@')[-1]}")
    else:
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 30})
except Exception as e:
    fallback_url = "sqlite:///./pms.db"
    print(f"PostgreSQL connection failed ({e}). Falling back to local SQLite database: {fallback_url}")
    DATABASE_URL = fallback_url
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 30})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
