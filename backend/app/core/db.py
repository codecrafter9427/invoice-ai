"""SQLAlchemy engine/session placeholders — schema not implemented yet."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Declarative base for future Invoice AI models."""


def get_db() -> Generator[Session, None, None]:
    """Yield a DB session. Models/migrations are Coming Soon."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
