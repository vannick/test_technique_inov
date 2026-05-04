"""Routes de l'agent: dialogue (/chat) et introspection des outils (/tools)."""
from fastapi import APIRouter, HTTPException, Depends
from loguru import logger

from src.models.schemas import ChatIn, ChatOut
from src.security import get_current_user
from src.services.agent import run_agent
from src.tools.handlers import TOOLS

router = APIRouter(prefix="/agent", tags=["agent"])


@router.get("/tools", summary="Lister les outils disponibles pour l'agent")
def list_tools() -> list[dict]:
    """Renvoie la liste des outils exposés au LLM avec leur schéma d'arguments.

    - `name`: identifiant de l'outil appelé par le modèle.
    - `description`: docstring utilisée par le LLM pour décider quand l'invoquer.
    - `args_schema`: schéma JSON des paramètres attendus (généré depuis la signature).
    """
    return [
        {
            "name": t.name,
            "description": t.description,
            "args_schema": t.args_schema.schema() if t.args_schema else {},
        }
        for t in TOOLS
    ]


@router.post("/chat", response_model=ChatOut, summary="Dialoguer avec l'agent")
def chat(payload: ChatIn, current_user: dict = Depends(get_current_user)) -> ChatOut:
    """Envoie un message à l'agent et renvoie sa réponse.

    - Si `session_id` est null, le serveur en génère un.
    - L'historique de la session est injecté automatiquement comme contexte.
    - `tool_used` indique le dernier outil appelé (null si simple réponse texte).
    - Codes: 503 si LLM indisponible (clé manquante), 500 sur erreur interne.
    """
    sid = str(payload.session_id) if payload.session_id else None
    try:
        result = run_agent(sid, payload.message, user_id=current_user["sub"])
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        logger.exception(f"Erreur agent: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur agent: {e}") from e
    return ChatOut(**result)
