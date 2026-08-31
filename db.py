import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

try:
    from config import settings
except ImportError:
    from .config import settings

# Resolve database URL
raw_db_url = settings.DATABASE_URL if (settings and settings.DATABASE_URL) else "sqlite:///./qa_agent.db"
# Normalize legacy postgres:// URI scheme to postgresql:// for SQLAlchemy compatibility
if raw_db_url.startswith("postgres://"):
    raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)

db_url = raw_db_url
connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}

engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False,
)

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


def init_db():
    """Ensure database schema exists using Alembic or Base metadata."""
    try:
        from alembic.config import Config
        from alembic import command
        alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "alembic.ini"))
        command.upgrade(alembic_cfg, "head")
    except Exception:
        try:
            from models import Base
        except ImportError:
            from .models import Base
        Base.metadata.create_all(bind=engine)
