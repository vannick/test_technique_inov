"""Route /agent/chat — point d'entrée principal de l'agent IA."""
from fastapi import APIRouter, HTTPException

from src.models.schemas import ChatIn, ChatOut
from src.services.agent import run_agent

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/chat", response_model=ChatOut)
def chat(payload: ChatIn) -> ChatOut:
    sid = str(payload.session_id) if payload.session_id else None
    try:
        result = run_agent(sid, payload.message)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Erreur agent: {e}") from e
    return ChatOut(**result)
