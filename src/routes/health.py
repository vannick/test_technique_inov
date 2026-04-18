"""Route /health."""
from fastapi import APIRouter
from sqlalchemy import text

from src.config import get_settings
from src.db.database import engine

router = APIRouter(tags=["health"])


@router.get("/health", summary="Santé de l'API et de ses dépendances")
def health():
    """Indique l'état de l'API et la connectivité de ses dépendances.

    - `status`: 'ok' si toutes les dépendances critiques répondent, sinon 'degraded'.
    - `database`: résultat d'un ping `SELECT 1` sur la base.
    - `calendar_backend`: backend agenda actif ('db' ou 'caldav').
    - `llm_configured`: vrai si une clé Groq est présente dans la config.
    """
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
        "calendar_backend": settings.calendar_backend,
        "llm_configured": bool(settings.groq_api_key),
    }
