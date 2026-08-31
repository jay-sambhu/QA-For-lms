from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

try:
    from config import settings
except ImportError:
    from .config import settings

# PostgreSQL engine (SQLAlchemy) – respects DATABASE_URL env var, falls back to SQLite file
db_url = settings.DATABASE_URL if (settings and settings.DATABASE_URL) else "sqlite:///./qa_agent.db"
connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}



engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False,
)

# Scoped session factory for thread‑local sessions (compatible with FastAPI)
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

try:
    try:
        from models import Base
    except ImportError:
        from .models import Base
    Base.metadata.create_all(bind=engine)
except Exception:
    pass


def get_db():
    """FastAPI dependency that yields a SQLAlchemy session.
    The session is automatically closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

