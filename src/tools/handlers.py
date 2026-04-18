"""Outils exposés à l'agent, déclarés comme LangChain Tools via le décorateur @tool.

Les signatures typées + docstrings servent directement de schéma JSON pour le LLM:
LangChain génère automatiquement la définition OpenAI-compatible des fonctions.
"""
import json
from typing import Optional

from langchain_core.tools import tool
from langchain_groq import ChatGroq

from src.config import get_settings
from src.services.calendar import get_calendar_repository


@tool
def get_agenda(date: Optional[str] = None, range: Optional[str] = None) -> str:
    """Liste les événements de l'agenda.

    Args:
        date: Filtre une date précise au format YYYY-MM-DD.
        range: Plage prédéfinie. Valeur acceptée: 'week' pour les 7 prochains jours.
    """
    repo = get_calendar_repository()
    events = repo.list_events(date=date, range_=range)
    return json.dumps([e.model_dump() for e in events], ensure_ascii=False)


@tool
def create_event(
    title: str,
    date: str,
    time: str,
    participants: str = "",
    notes: str = "",
) -> str:
    """Crée un événement dans l'agenda.

    Args:
        title: Intitulé de l'événement.
        date: Date au format YYYY-MM-DD.
        time: Heure au format HH:MM.
        participants: Liste de participants séparés par une virgule.
        notes: Notes libres associées à l'événement.
    """
    repo = get_calendar_repository()
    ev = repo.create_event(
        title=title, date=date, time=time, participants=participants, notes=notes
    )
    return json.dumps(ev.model_dump(), ensure_ascii=False)


@tool
def update_event(
    event_id: str,
    title: Optional[str] = None,
    date: Optional[str] = None,
    time: Optional[str] = None,
    participants: Optional[str] = None,
    notes: Optional[str] = None,
) -> str:
    """Met à jour un ou plusieurs champs d'un événement existant.

    À utiliser pour décaler, renommer ou modifier un rendez-vous. Appeler
    `get_agenda` d'abord si l'id n'est pas connu.
    """
    repo = get_calendar_repository()
    patch = {
        k: v for k, v in {
            "title": title, "date": date, "time": time,
            "participants": participants, "notes": notes,
        }.items() if v is not None
    }
    ev = repo.update_event(str(event_id), patch)
    if not ev:
        return json.dumps({"error": "Événement introuvable", "event_id": event_id}, ensure_ascii=False)
    return json.dumps(ev.model_dump(), ensure_ascii=False)


@tool
def delete_event(event_id: str) -> str:
    """Supprime un événement de l'agenda par son identifiant.

    À utiliser quand l'utilisateur demande d'annuler ou supprimer un rendez-vous.
    Appeler `get_agenda` d'abord si l'id n'est pas connu.
    """
    repo = get_calendar_repository()
    ok = repo.delete_event(str(event_id))
    return json.dumps({"deleted": ok, "event_id": event_id}, ensure_ascii=False)


@tool
def summarize_document(text: str, focus: str = "") -> str:
    """Produit une synthèse structurée d'un document fourni en texte brut.

    Retourne un JSON avec les clés: resume, points_cles, decisions, actions.

    Args:
        text: Contenu textuel du document à synthétiser.
        focus: Axe de la synthèse (optionnel).
    """
    settings = get_settings()
    llm = ChatGroq(
        api_key=settings.groq_api_key, model=settings.groq_model, temperature=0.2,
        model_kwargs={"response_format": {"type": "json_object"}},
    )
    prompt = (
        "Tu es un assistant qui produit des synthèses structurées de documents. "
        "Retourne STRICTEMENT un JSON avec les clés: 'resume' (str), "
        "'points_cles' (list[str]), 'decisions' (list[str]), 'actions' (list[str]). "
        f"Axe optionnel: {focus}\n\nDocument:\n{text}"
    )
    return llm.invoke(prompt).content or "{}"


# Liste exposée à l'orchestrateur LangChain.
TOOLS = [get_agenda, create_event, update_event, delete_event, summarize_document]
