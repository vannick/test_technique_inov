"""Tests de la mémoire de session (services/memory.py) et de la route historique."""
import uuid

from src.services import memory


def test_ensure_session_creates_new_id_when_none():
    sid = memory.ensure_session(None)
    # UUID4 valide.
    assert uuid.UUID(sid)


def test_ensure_session_returns_existing_id():
    first = memory.ensure_session(None)
    again = memory.ensure_session(first)
    assert first == again


def test_ensure_session_accepts_unknown_id_and_registers_it():
    # Permet de reprendre une session connue côté client sans 404.
    given = str(uuid.uuid4())
    assert memory.ensure_session(given) == given


def test_add_and_retrieve_history_ordered():
    sid = memory.ensure_session(None)
    memory.add_message(sid, "user", "premier")
    memory.add_message(sid, "assistant", "reponse 1", tool_used="get_agenda")
    memory.add_message(sid, "user", "second")
    msgs = memory.get_history(sid)
    assert [m.content for m in msgs] == ["premier", "reponse 1", "second"]
    assert msgs[1].tool_used == "get_agenda"


def test_turn_count_counts_only_user_messages():
    sid = memory.ensure_session(None)
    memory.add_message(sid, "user", "q1")
    memory.add_message(sid, "assistant", "r1")
    memory.add_message(sid, "user", "q2")
    memory.add_message(sid, "assistant", "r2")
    assert memory.get_turn_count(sid) == 2


def test_history_route_returns_messages(client):
    sid = memory.ensure_session(None)
    memory.add_message(sid, "user", "salut")
    memory.add_message(sid, "assistant", "bonjour")
    resp = client.get(f"/session/{sid}/history")
    assert resp.status_code == 200
    contents = [m["content"] for m in resp.json()]
    assert contents == ["salut", "bonjour"]


def test_history_route_404_for_unknown_session(client):
    resp = client.get(f"/session/{uuid.uuid4()}/history")
    assert resp.status_code == 404


def test_history_route_422_for_invalid_uuid(client):
    resp = client.get("/session/not-a-uuid/history")
    assert resp.status_code == 422
