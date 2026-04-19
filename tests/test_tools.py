"""Tests des tools LangChain (handlers), exécutés contre le backend DB."""
import json
from datetime import date, timedelta

from src.tools.handlers import create_event, delete_event, get_agenda, update_event


def _invoke(tool, **kwargs) -> dict | list:
    """Appelle un tool LangChain et renvoie la sortie JSON désérialisée."""
    raw = tool.invoke(kwargs)
    return json.loads(raw)


def test_get_agenda_returns_empty_list():
    assert _invoke(get_agenda) == []


def test_create_event_and_list():
    d = (date.today() + timedelta(days=1)).isoformat()
    ev = _invoke(
        create_event,
        title="RDV",
        date=d,
        time="10:00",
        participants="Alice",
        notes="n",
    )
    assert ev["title"] == "RDV"
    assert ev["date"] == d
    # Le tool get_agenda doit retrouver l'événement.
    listed = _invoke(get_agenda)
    assert len(listed) == 1
    assert listed[0]["id"] == ev["id"]


def test_update_event_changes_title():
    d = (date.today() + timedelta(days=1)).isoformat()
    created = _invoke(create_event, title="Old", date=d, time="09:00")
    updated = _invoke(update_event, event_id=created["id"], title="New")
    assert updated["title"] == "New"


def test_update_event_unknown_returns_error_json():
    out = _invoke(update_event, event_id="9999", title="x")
    assert out.get("error")


def test_delete_event_removes_it():
    d = (date.today() + timedelta(days=1)).isoformat()
    created = _invoke(create_event, title="Tmp", date=d, time="09:00")
    out = _invoke(delete_event, event_id=created["id"])
    assert out == {"deleted": True, "event_id": created["id"]}
    assert _invoke(get_agenda) == []


def test_delete_event_unknown_returns_false():
    out = _invoke(delete_event, event_id="9999")
    assert out == {"deleted": False, "event_id": "9999"}


def test_get_agenda_filter_by_date():
    d1 = (date.today() + timedelta(days=1)).isoformat()
    d2 = (date.today() + timedelta(days=2)).isoformat()
    _invoke(create_event, title="A", date=d1, time="09:00")
    _invoke(create_event, title="B", date=d2, time="09:00")
    only_d1 = _invoke(get_agenda, date=d1)
    assert [e["title"] for e in only_d1] == ["A"]
