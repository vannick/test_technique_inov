"""Tests de l'orchestrateur agent avec un exécuteur LangChain mocké.

On ne veut pas d'appel réseau à Groq: on substitue `_build_executor` par un
double qui émule `AgentExecutor.invoke` (succès, retries, erreurs).
"""
from unittest.mock import MagicMock, patch

import httpx
import pytest
from groq import BadRequestError
from langchain_core.agents import AgentAction
from langchain_core.messages import AIMessage

from src.services import agent as agent_module


def _fake_step(tool_name: str = "get_agenda") -> tuple:
    """Reproduit la structure `(AgentAction, observation)` des `intermediate_steps`."""
    action = AgentAction(tool=tool_name, tool_input={}, log="")
    return (action, "observation")


def _badrequest(message: str) -> BadRequestError:
    """Fabrique une BadRequestError minimale compatible avec l'API groq."""
    req = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    resp = httpx.Response(400, request=req, json={"error": {"message": message}})
    return BadRequestError(message=message, response=resp, body=None)


@pytest.fixture
def fake_executor():
    """Patch `_build_executor` pour renvoyer un MagicMock configurable par test."""
    exec_mock = MagicMock()
    with patch.object(agent_module, "_build_executor", return_value=exec_mock):
        yield exec_mock


def test_run_agent_returns_expected_shape(fake_executor):
    fake_executor.invoke.return_value = {
        "output": "Voici votre agenda.",
        "intermediate_steps": [_fake_step("get_agenda")],
    }
    out = agent_module.run_agent(session_id=None, user_message="liste mon agenda")
    assert out["response"] == "Voici votre agenda."
    assert out["tool_used"] == "get_agenda"
    assert out["turn"] == 1
    assert out["session_id"]


def test_run_agent_persists_history(fake_executor, client):
    fake_executor.invoke.return_value = {
        "output": "ok",
        "intermediate_steps": [],
    }
    out = agent_module.run_agent(session_id=None, user_message="hello")
    resp = client.get(f"/session/{out['session_id']}/history")
    assert resp.status_code == 200
    roles = [m["role"] for m in resp.json()]
    assert roles == ["user", "assistant"]


def test_run_agent_no_tool_used_when_no_steps(fake_executor):
    fake_executor.invoke.return_value = {"output": "Bonjour !", "intermediate_steps": []}
    out = agent_module.run_agent(session_id=None, user_message="salut")
    assert out["tool_used"] is None


def test_retry_on_malformed_tool_call(fake_executor):
    """Le premier appel échoue avec l'erreur Groq typique, le second passe."""
    fake_executor.invoke.side_effect = [
        _badrequest("tool call validation failed: attempted to call tool 'x {...}' "
                    "which was not in request.tools"),
        {"output": "ok", "intermediate_steps": [_fake_step()]},
    ]
    out = agent_module.run_agent(session_id=None, user_message="test")
    assert out["response"] == "ok"
    assert fake_executor.invoke.call_count == 2


def test_retry_on_typeerror_from_null_arguments(fake_executor):
    """Cas où le LLM renvoie `arguments: "null"`, casse le parser LangChain."""
    fake_executor.invoke.side_effect = [
        TypeError("argument of type 'NoneType' is not iterable"),
        {"output": "ok", "intermediate_steps": [_fake_step()]},
    ]
    out = agent_module.run_agent(session_id=None, user_message="test")
    assert out["response"] == "ok"
    assert fake_executor.invoke.call_count == 2


def test_retry_gives_up_after_max_attempts(fake_executor):
    fake_executor.invoke.side_effect = _badrequest(
        "tool call validation failed: was not in request.tools"
    )
    with pytest.raises(BadRequestError):
        agent_module.run_agent(session_id=None, user_message="test")
    # 1 tentative initiale + MAX_AGENT_RETRIES retries.
    assert fake_executor.invoke.call_count == 1 + agent_module.MAX_AGENT_RETRIES


def test_non_tool_format_error_is_not_retried(fake_executor):
    """Les autres erreurs (rate limit, auth, etc.) doivent remonter immédiatement."""
    fake_executor.invoke.side_effect = RuntimeError("boom")
    with pytest.raises(RuntimeError):
        agent_module.run_agent(session_id=None, user_message="test")
    assert fake_executor.invoke.call_count == 1


def test_sanitize_tool_calls_fixes_null_arguments_string():
    """Le LLM renvoie parfois `arguments: "null"` — on doit récrire en `"{}"`."""
    msg = AIMessage(
        content="",
        additional_kwargs={
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "get_agenda", "arguments": "null"},
                }
            ]
        },
    )
    out = agent_module.sanitize_tool_calls(msg)
    assert out.additional_kwargs["tool_calls"][0]["function"]["arguments"] == "{}"


def test_sanitize_tool_calls_fixes_empty_string_arguments():
    """Autre artefact: `arguments: ""` (vide) doit aussi être transformé en `"{}"`."""
    msg = AIMessage(
        content="",
        additional_kwargs={
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "get_agenda", "arguments": ""},
                }
            ]
        },
    )
    out = agent_module.sanitize_tool_calls(msg)
    assert out.additional_kwargs["tool_calls"][0]["function"]["arguments"] == "{}"


def test_sanitize_tool_calls_is_noop_for_valid_message():
    msg = AIMessage(
        content="",
        additional_kwargs={
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "get_agenda", "arguments": '{"date": "2026-01-01"}'},
                }
            ]
        },
    )
    out = agent_module.sanitize_tool_calls(msg)
    assert (
        out.additional_kwargs["tool_calls"][0]["function"]["arguments"]
        == '{"date": "2026-01-01"}'
    )


def test_sanitize_tool_calls_passthrough_for_non_ai_message():
    from langchain_core.messages import HumanMessage
    msg = HumanMessage(content="bonjour")
    assert agent_module.sanitize_tool_calls(msg) is msg


def test_chat_endpoint_returns_503_without_api_key(client, monkeypatch):
    """Si la clé LLM est absente, /agent/chat renvoie 503."""
    from src.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_api_key", "")
    resp = client.post(
        "/agent/chat",
        json={"session_id": None, "message": "test"},
    )
    assert resp.status_code == 503
