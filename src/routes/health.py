"""Route /health."""
from fastapi import APIRouter
from sqlalchemy import text

from src.config import get_settings
from src.db.database import engine

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    settings = get_settings()
    db_ok = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "up" if db_ok else "down",
        "calendar_backend": settings.calendar_backend
    }
