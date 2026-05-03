"""Configuration SQLAlchemy : engine, session, init_db."""
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import get_settings
from src.models import Base  # noqa: F401  # assure que tous les modèles sont enregistrés

settings = get_settings()

# Assurer l'existence du dossier pour SQLite
if settings.database_url.startswith("sqlite"):
    db_path = settings.database_url.split("///")[-1]
    Path(os.path.dirname(db_path) or ".").mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    """Crée les tables si absentes."""
    from src.models import orm  # noqa: F401 — enregistre les modèles

    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
