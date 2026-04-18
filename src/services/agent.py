"""Orchestrateur de l'agent: pilote le tool calling via Groq."""
import json
from datetime import date
from typing import Optional

from groq import Groq
from loguru import logger

from src.config import get_settings
from src.services import memory
from src.tools.definitions import TOOL_DEFINITIONS
from src.tools.handlers import TOOL_HANDLERS

SYSTEM_PROMPT = (
    "Tu es un assistant de direction en français. Tu aides l'utilisateur à gérer son agenda "
    "et à synthétiser des documents. Tu DOIS utiliser les outils fournis dès qu'ils sont "
    "pertinents (ne jamais inventer d'événements: appelle `get_agenda`). "
    "Réponds de manière naturelle, concise et professionnelle. "
    f"Date du jour: {date.today().isoformat()}."
)

MAX_TOOL_LOOPS = 4


def _build_messages(session_id: str, user_message: str) -> list[dict]:
    history = memory.get_history(session_id)
    msgs: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in history:
        if m.role in ("user", "assistant"):
            msgs.append({"role": m.role, "content": m.content})
    msgs.append({"role": "user", "content": user_message})
    return msgs


def run_agent(session_id: Optional[str], user_message: str) -> dict:
    settings = get_settings()
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY manquante — impossible d'appeler le LLM.")

    sid = memory.ensure_session(session_id)
    memory.add_message(sid, "user", user_message)

    client = Groq(api_key=settings.groq_api_key)
    messages = _build_messages(sid, user_message)

    tool_used: Optional[str] = None

    for _ in range(MAX_TOOL_LOOPS):
        resp = client.chat.completions.create(
            model=settings.groq_model,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            temperature=0.3,
        )
        msg = resp.choices[0].message
        tool_calls = msg.tool_calls or []

        if not tool_calls:
            final = msg.content or ""
            memory.add_message(sid, "assistant", final, tool_used=tool_used)
            turn = memory.get_turn_count(sid)
            return {"session_id": sid, "response": final, "tool_used": tool_used, "turn": turn}

        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in tool_calls
            ],
        })

        for tc in tool_calls:
            name = tc.function.name
            tool_used = name  # on garde le dernier outil invoqué
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            handler = TOOL_HANDLERS.get(name)
            if not handler:
                result = json.dumps({"error": f"Outil inconnu: {name}"})
            else:
                try:
                    result = handler(args)
                except Exception as e:  # noqa: BLE001
                    logger.exception(f"Erreur outil {name}")
                    result = json.dumps({"error": str(e)})
            messages.append({"role": "tool", "tool_call_id": tc.id, "name": name, "content": result})

    # Sortie de boucle forcée
    fallback = "Je n'ai pas pu finaliser la demande après plusieurs appels outils."
    memory.add_message(sid, "assistant", fallback, tool_used=tool_used)
    return {
        "session_id": sid, "response": fallback,
        "tool_used": tool_used, "turn": memory.get_turn_count(sid),
    }
