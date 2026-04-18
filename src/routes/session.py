"""Route /session/{id}/history."""
from uuid import UUID

from fastapi import APIRouter, HTTPException

from src.db.database import SessionLocal
from src.models.orm import ChatSession
from src.models.schemas import MessageOut
from src.services import memory

router = APIRouter(prefix="/session", tags=["session"])


@router.get(
    "/{session_id}/history",
    response_model=list[MessageOut],
    summary="Historique d'une session de chat",
)
def history(session_id: UUID):
    """Renvoie tous les messages d'une session, ordonnés chronologiquement.

    - Validation UUID au format de l'URL (422 si invalide).
    - 404 si la session n'existe pas.
    """
    sid = str(session_id)
    with SessionLocal() as db:
        if not db.get(ChatSession, sid):
            raise HTTPException(status_code=404, detail="Session inconnue")
    msgs = memory.get_history(sid)
    return [MessageOut(role=m.role, content=m.content, timestamp=m.timestamp) for m in msgs]
