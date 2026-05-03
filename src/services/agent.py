"""Orchestrateur de l'agent via LangChain + Groq.

Construit manuellement le pipeline de tool calling (au lieu d'utiliser
`create_tool_calling_agent`) afin d'intercaler un *sanitizer* entre la sortie
du LLM et le parser: `llama-3.3-70b-versatile` produit parfois un tool call
dont `function.arguments` vaut la chaîne `"null"`, que LangChain décode en
`None` — ce qui casse ensuite `parse_ai_message_to_tool_action` avec
`TypeError: argument of type 'NoneType' is not iterable`.

Autres stabilisations: `temperature=0`, prompt explicite, retry sur
`BadRequestError` Groq (cas où le nom de l'outil est concaténé aux args).
"""
from datetime import date
from typing import Optional

from groq import BadRequestError
from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad.tools import format_to_tool_messages
from langchain.agents.output_parsers.tools import ToolsAgentOutputParser
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_groq import ChatGroq
from loguru import logger

from src.config import get_settings
from src.services import memory
from src.tools.handlers import TOOLS

SYSTEM_PROMPT = (
    "Tu es une assistante de direction en français appelée INOVIE. Tu aides l'utilisateur "
    "à gérer son agenda et à synthétiser des documents. "
    "Réponds de manière naturelle, concise et professionnelle.\n"
    "RÈGLES STRICTES:\n"
    "1. Utilise TOUJOURS les outils fournis pour toute opération sur l'agenda: "
    "`get_agenda`, `create_event`, `update_event`, `delete_event`. "
    "N'invente JAMAIS d'événement ni d'identifiant.\n"
    "2. Avant toute modification ou suppression, appelle d'abord `get_agenda` "
    "pour récupérer l'`id` exact de l'événement.\n"
    "3. Format des tool calls: respecte STRICTEMENT le nom exact de l'outil "
    "(exemple: `get_agenda`), sans suffixe, sans arguments accolés au nom.\n"
    "4. Date du jour: {today}. Toutes les dates relatives (aujourd'hui, demain, "
    "la semaine prochaine) doivent être calculées à partir de cette date."
)

MAX_TOOL_LOOPS = 4

MAX_AGENT_RETRIES = 2


def _build_chat_history(session_id: str) -> list:
    """Convertit l'historique DB en messages LangChain (user/assistant uniquement)."""
    msgs: list = []
    for m in memory.get_history(session_id):
        if m.role == "user":
            msgs.append(HumanMessage(content=m.content))
        elif m.role == "assistant":
            msgs.append(AIMessage(content=m.content))
    return msgs


def sanitize_tool_calls(message: BaseMessage) -> BaseMessage:
    """Normalise les tool calls retournés par le LLM avant le parser LangChain.

    Corrige deux artefacts observés sur `llama-3.3-70b-versatile`:
    - `additional_kwargs.tool_calls[*].function.arguments == "null"`
      -> remplacé par `"{}"` (dict vide JSON).
    - `tool_calls[*].args is None`
      -> remplacé par `{}`.

    Sans cette normalisation, `parse_ai_message_to_tool_action` exécute
    `"__arg1" in None` et lève un `TypeError`.
    """
    if not isinstance(message, (AIMessage, AIMessageChunk)):
        return message

    raw_calls = message.additional_kwargs.get("tool_calls") or []
    for call in raw_calls:
        fn = call.get("function") or {}
        if fn.get("arguments") in (None, "null", ""):
            fn["arguments"] = "{}"
            call["function"] = fn

    for call in list(getattr(message, "tool_calls", []) or []):
        if call.get("args") is None:
            call["args"] = {}

    return message


def _build_executor() -> AgentExecutor:
    """Instancie l'AgentExecutor LangChain: LLM  + prompt + outils.

    Pipeline reconstruit manuellement pour intercaler `sanitize_tool_calls`
    entre `llm_with_tools` et `ToolsAgentOutputParser` (cf. docstring du module).
    """
    settings = get_settings()
    # Température à 0 pour maximiser la stabilité du format tool-call.
    llm = ChatGroq(
        api_key=settings.llm_api_key, model=settings.llm_model, temperature=0,
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])
    llm_with_tools = llm.bind_tools(TOOLS)
    agent = (
        RunnablePassthrough.assign(
            agent_scratchpad=lambda x: format_to_tool_messages(x["intermediate_steps"])
        )
        | prompt
        | llm_with_tools
        | RunnableLambda(sanitize_tool_calls)
        | ToolsAgentOutputParser()
    )
    return AgentExecutor(
        agent=agent, tools=TOOLS,
        max_iterations=MAX_TOOL_LOOPS,
        return_intermediate_steps=True,
        verbose=False,
    )


def _is_tool_call_format_error(exc: BaseException) -> bool:
    """Détecte les tool calls malformés par le LLM, deux variantes observées sur
    """
    if isinstance(exc, BadRequestError):
        msg = str(exc).lower()
        return "tool call validation failed" in msg or "was not in request.tools" in msg
    if isinstance(exc, TypeError):
        return "'nonetype' is not iterable" in str(exc).lower()
    return False


def _invoke_with_retry(executor: AgentExecutor, payload: dict) -> dict:
    """Invoque l'executor en retentant jusqu'à `MAX_AGENT_RETRIES` fois
    si le LLM produit un tool call mal formé.
    """
    last_exc: Optional[BaseException] = None
    for attempt in range(1 + MAX_AGENT_RETRIES):
        try:
            return executor.invoke(payload)
        except Exception as e:  # noqa: BLE001
            # On ne retente que sur l'erreur de parsing tool-call; tout le reste remonte.
            if not _is_tool_call_format_error(e):
                raise
            last_exc = e
            logger.warning(
                f"Tool call malformé côté LLM (tentative {attempt + 1}/"
                f"{1 + MAX_AGENT_RETRIES}). Nouvelle tentative…"
            )
    assert last_exc is not None
    raise last_exc


def run_agent(session_id: Optional[str], user_message: str, user_id: Optional[str] = None) -> dict:
    """Exécute un tour de dialogue complet avec tool calling.

    - Vérifie la présence de la clé LLM (sinon RuntimeError pour HTTP 503 en amont).
    - Assure la session, persiste le message utilisateur dans la mémoire.
    - Invoque l'AgentExecutor qui orchestre la boucle appels LLM / exécution tools.
    - `tool_used` = dernier outil appelé, extrait des `intermediate_steps`.
    - Renvoie `{session_id, response, tool_used, turn}` pour la route `/agent/chat`.
    """
    settings = get_settings()
    if not settings.llm_api_key:
        raise RuntimeError("GROQ_API_KEY manquante — impossible d'appeler le LLM.")

    sid = memory.ensure_session(session_id)
    memory.add_message(sid, "user", user_message)

    executor = _build_executor()
    payload = {
        "input": user_message,
        "chat_history": _build_chat_history(sid),
        "today": date.today().isoformat(),
        "user_id": user_id,
    }
    result = _invoke_with_retry(executor, payload)

    steps = result.get("intermediate_steps") or []
    tool_used: Optional[str] = steps[-1][0].tool if steps else None
    final = result.get("output") or ""

    memory.add_message(sid, "assistant", final, tool_used=tool_used)
    return {
        "session_id": sid, "response": final,
        "tool_used": tool_used, "turn": memory.get_turn_count(sid),
    }
