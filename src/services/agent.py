"""Orchestrateur de l'agent via LangChain + Groq.

Utilise `create_tool_calling_agent` + `AgentExecutor` pour piloter la boucle
de tool calling. L'historique de session est persisté côté DB (cf. `memory`)
puis réinjecté dans l'agent sous forme de messages LangChain.
"""
from datetime import date
from typing import Optional

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq

from src.config import get_settings
from src.services import memory
from src.tools.handlers import TOOLS

SYSTEM_PROMPT = (
    "Tu es un assistant de direction en français. Tu aides l'utilisateur à gérer son agenda "
    "et à synthétiser des documents. Tu DOIS utiliser les outils fournis dès qu'ils sont "
    "pertinents (ne jamais inventer d'événements: appelle `get_agenda`). "
    "Réponds de manière naturelle, concise et professionnelle. "
    "Date du jour: {today}."
)

MAX_TOOL_LOOPS = 4


def _build_chat_history(session_id: str) -> list:
    """Convertit l'historique DB en messages LangChain (user/assistant uniquement)."""
    msgs: list = []
    for m in memory.get_history(session_id):
        if m.role == "user":
            msgs.append(HumanMessage(content=m.content))
        elif m.role == "assistant":
            msgs.append(AIMessage(content=m.content))
    return msgs


def _build_executor() -> AgentExecutor:
    """Instancie l'AgentExecutor LangChain: LLM Groq + prompt + 5 outils.

    Le prompt inclut des placeholders pour l'historique (`chat_history`),
    l'entrée utilisateur (`input`) et les étapes intermédiaires (`agent_scratchpad`)
    pilotées par LangChain entre chaque appel tool.
    """
    settings = get_settings()
    llm = ChatGroq(
        api_key=settings.groq_api_key, model=settings.groq_model, temperature=0.3,
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])
    agent = create_tool_calling_agent(llm, TOOLS, prompt)
    return AgentExecutor(
        agent=agent, tools=TOOLS,
        max_iterations=MAX_TOOL_LOOPS,
        return_intermediate_steps=True,
        verbose=False,
    )


def run_agent(session_id: Optional[str], user_message: str) -> dict:
    """Exécute un tour de dialogue complet avec tool calling.

    - Vérifie la présence de la clé LLM (sinon RuntimeError pour HTTP 503 en amont).
    - Assure la session, persiste le message utilisateur dans la mémoire.
    - Invoque l'AgentExecutor qui orchestre la boucle appels LLM / exécution tools.
    - `tool_used` = dernier outil appelé, extrait des `intermediate_steps`.
    - Renvoie `{session_id, response, tool_used, turn}` pour la route `/agent/chat`.
    """
    settings = get_settings()
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY manquante — impossible d'appeler le LLM.")

    sid = memory.ensure_session(session_id)
    memory.add_message(sid, "user", user_message)

    executor = _build_executor()
    result = executor.invoke({
        "input": user_message,
        "chat_history": _build_chat_history(sid),
        "today": date.today().isoformat(),
    })

    steps = result.get("intermediate_steps") or []
    tool_used: Optional[str] = steps[-1][0].tool if steps else None
    final = result.get("output") or ""

    memory.add_message(sid, "assistant", final, tool_used=tool_used)
    return {
        "session_id": sid, "response": final,
        "tool_used": tool_used, "turn": memory.get_turn_count(sid),
    }
