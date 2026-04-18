"""Implémentations concrètes des outils invoqués par l'agent."""
import json
from typing import Any

from groq import Groq

from src.config import get_settings
from src.services.calendar import get_calendar_repository


def tool_get_agenda(args: dict) -> str:
    repo = get_calendar_repository()
    events = repo.list_events(date=args.get("date"), range_=args.get("range"))
    return json.dumps([e.model_dump() for e in events], ensure_ascii=False)


def tool_create_event(args: dict) -> str:
    repo = get_calendar_repository()
    ev = repo.create_event(
        title=args["title"],
        date=args["date"],
        time=args["time"],
        participants=args.get("participants", ""),
        notes=args.get("notes", ""),
    )
    return json.dumps(ev.model_dump(), ensure_ascii=False)


def tool_update_event(args: dict) -> str:
    repo = get_calendar_repository()
    event_id = str(args.pop("event_id"))
    patch = {k: v for k, v in args.items() if v is not None}
    ev = repo.update_event(event_id, patch)
    if not ev:
        return json.dumps({"error": "Événement introuvable", "event_id": event_id}, ensure_ascii=False)
    return json.dumps(ev.model_dump(), ensure_ascii=False)


def tool_delete_event(args: dict) -> str:
    repo = get_calendar_repository()
    ok = repo.delete_event(str(args["event_id"]))
    return json.dumps({"deleted": ok, "event_id": args["event_id"]}, ensure_ascii=False)


def tool_summarize_document(args: dict) -> str:
    """Synthèse structurée via un deuxième appel LLM (output JSON)."""
    settings = get_settings()
    client = Groq(api_key=settings.groq_api_key)
    focus = args.get("focus", "")
    prompt = (
        "Tu es un assistant qui produit des synthèses structurées de documents. "
        "Retourne STRICTEMENT un JSON avec les clés: 'resume' (str), "
        "'points_cles' (list[str]), 'decisions' (list[str]), 'actions' (list[str]). "
        f"Axe optionnel: {focus}\n\nDocument:\n{args['text']}"
    )
    resp = client.chat.completions.create(
        model=settings.groq_model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    return resp.choices[0].message.content or "{}"


TOOL_HANDLERS: dict[str, Any] = {
    "get_agenda": tool_get_agenda,
    "create_event": tool_create_event,
    "update_event": tool_update_event,
    "delete_event": tool_delete_event,
    "summarize_document": tool_summarize_document,
}
