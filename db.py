import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

try:
    from config import settings
except ImportError:
    from .config import settings

raw_db_url = os.environ.get("DATABASE_URL") or (settings.DATABASE_URL if (settings and settings.DATABASE_URL) else "sqlite:///./qa_agent.db")
# Normalize legacy postgres:// URI scheme to postgresql:// for SQLAlchemy compatibility
if raw_db_url.startswith("postgres://"):
    raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)

db_url = raw_db_url

if db_url.startswith("sqlite"):
    engine_kwargs = {
        "connect_args": {"check_same_thread": False},
        "pool_pre_ping": True,
        "echo": False,
    }
else:
    # Production-grade PostgreSQL connection pooling for concurrent API & Celery workers
    engine_kwargs = {
        "pool_size": int(os.environ.get("DB_POOL_SIZE", 20)),
        "max_overflow": int(os.environ.get("DB_MAX_OVERFLOW", 10)),
        "pool_recycle": int(os.environ.get("DB_POOL_RECYCLE", 1800)),
        "pool_pre_ping": True,
        "echo": False,
    }

engine = create_engine(db_url, **engine_kwargs)

# Scoped session factory for thread‑safe sessions (compatible with FastAPI & Celery workers)
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))


def get_db():
    """FastAPI dependency that yields a SQLAlchemy session.
    The session is automatically closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session():
    """Context manager for standalone database operations with auto commit/rollback."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
