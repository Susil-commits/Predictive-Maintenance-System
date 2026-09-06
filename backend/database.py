import os
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Load .env variables
load_dotenv()

import random
import time
from .logging_config import logger as _root_logger, setup_logging

logger = logging.getLogger("pms.database")

def calculate_backoff(attempt: int, base_delay: float = 1.0, max_delay: float = 10.0) -> float:
    """Calculates exponential backoff delay with randomized jitter."""
    exp_delay = min(max_delay, base_delay * (2.0 ** (attempt - 1)))
    jitter = random.uniform(0.0, 0.3 * exp_delay)
    return exp_delay + jitter

def execute_with_retry(fn, max_retries: int = 3, base_delay: float = 0.5):
    """Executes a database operation with exponential backoff retry on transient failure."""
    for attempt in range(1, max_retries + 1):
        try:
            return fn()
        except Exception as e:
            if attempt == max_retries:
                logger.error(f"Database operation failed permanently after {max_retries} attempts: {e}")
                raise
            delay = calculate_backoff(attempt, base_delay=base_delay)
            logger.warning(f"Database transient error (attempt {attempt}/{max_retries}): {e}. Retrying in {delay:.2f}s...")
            time.sleep(delay)

_raw_db_url = os.getenv("DATABASE_URL")
if not _raw_db_url or not _raw_db_url.strip():
    raise RuntimeError(
        "CRITICAL DATABASE CONFIGURATION ERROR: DATABASE_URL environment variable is not set. "
        "Define DATABASE_URL in your environment or deployment dashboard."
    )
DATABASE_URL = _raw_db_url.strip()
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Attempt to create engine with retry and exponential backoff, fallback gracefully to SQLite
engine = None

if DATABASE_URL.startswith("postgresql"):
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            # Configure robust connection pooling for high-concurrency production workloads
            # Configured to pool_size=20, max_overflow=30 with env override support for cloud pooler limits
            db_pool_size = int(os.getenv("DB_POOL_SIZE", "20"))
            db_max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "30"))
            test_engine = create_engine(
                DATABASE_URL,
                connect_args={'connect_timeout': 10},
                pool_size=db_pool_size,
                max_overflow=db_max_overflow,
                pool_timeout=30,
                pool_recycle=300,
                pool_pre_ping=True
            )
            with test_engine.connect() as conn:
                pass
            engine = test_engine
            db_identifier = DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else "postgresql"
            logger.info(f"Connected to PostgreSQL database: {db_identifier}")
            break
        except Exception as err:
            logger.warning(f"PostgreSQL connection attempt {attempt}/{max_retries} failed: {err}")
            if attempt < max_retries:
                delay = calculate_backoff(attempt, base_delay=1.0)
                logger.info(f"Applying exponential backoff: sleeping {delay:.2f}s before reconnect attempt {attempt + 1}")
                time.sleep(delay)
            else:
                if os.getenv("RENDER") or os.getenv("ENVIRONMENT") == "production":
                    raise RuntimeError(f"Failed to connect to production PostgreSQL database at {DATABASE_URL}: {err}") from err
                fallback_url = "sqlite:///./pms.db"
                logger.error(f"All PostgreSQL connection attempts failed. Falling back to local SQLite database: {fallback_url}")
                DATABASE_URL = fallback_url
                engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 30})
else:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 30})
    logger.info(f"Using database: {DATABASE_URL}")

assert engine is not None

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
