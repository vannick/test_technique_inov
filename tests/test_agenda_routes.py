"""Tests des routes CRUD /agenda (backend DB)."""
from datetime import date, timedelta


def _event_payload(offset_days: int = 1, **overrides) -> dict:
    base = {
        "title": "Reunion test",
        "date": (date.today() + timedelta(days=offset_days)).isoformat(),
        "time": "10:00",
        "participants": "Alice, Bob",
        "notes": "Point hebdo",
    }
    base.update(overrides)
    return base


def test_create_event_returns_201_and_body(client):
    resp = client.post("/agenda", json=_event_payload())
    assert resp.status_code == 201
    ev = resp.json()
    assert ev["id"]
    assert ev["title"] == "Reunion test"
    assert ev["participants"] == "Alice, Bob"


def test_list_events_empty_by_default(client):
    resp = client.get("/agenda")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_events_after_create(client):
    client.post("/agenda", json=_event_payload(title="A"))
    client.post("/agenda", json=_event_payload(title="B", offset_days=2))
    resp = client.get("/agenda")
    assert resp.status_code == 200
    titles = [e["title"] for e in resp.json()]
    assert set(titles) == {"A", "B"}


def test_filter_by_date(client):
    d1 = (date.today() + timedelta(days=1)).isoformat()
    d2 = (date.today() + timedelta(days=3)).isoformat()
    client.post("/agenda", json=_event_payload(title="J+1"))
    client.post("/agenda", json=_event_payload(title="J+3", offset_days=3))
    resp = client.get(f"/agenda?date={d1}")
    data = resp.json()
    assert len(data) == 1
    assert data[0]["date"] == d1
    assert data[0]["title"] == "J+1"
    # Sanity: le second est bien dans la base à une autre date.
    resp2 = client.get(f"/agenda?date={d2}")
    assert len(resp2.json()) == 1


def test_filter_range_week(client):
    # J+2 inclus, J+10 exclu
    client.post("/agenda", json=_event_payload(title="proche", offset_days=2))
    client.post("/agenda", json=_event_payload(title="lointain", offset_days=10))
    resp = client.get("/agenda?range=week")
    titles = [e["title"] for e in resp.json()]
    assert "proche" in titles
    assert "lointain" not in titles


def test_patch_event_updates_fields(client):
    created = client.post("/agenda", json=_event_payload()).json()
    resp = client.patch(
        f"/agenda/{created['id']}",
        json={"title": "Nouveau titre", "notes": "maj"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Nouveau titre"
    assert body["notes"] == "maj"
    # Les champs non fournis restent inchangés.
    assert body["participants"] == "Alice, Bob"


def test_patch_unknown_event_returns_404(client):
    resp = client.patch("/agenda/9999", json={"title": "x"})
    assert resp.status_code == 404


def test_delete_event_returns_204(client):
    created = client.post("/agenda", json=_event_payload()).json()
    resp = client.delete(f"/agenda/{created['id']}")
    assert resp.status_code == 204
    # Plus présent ensuite.
    assert client.get("/agenda").json() == []


def test_delete_unknown_event_returns_404(client):
    resp = client.delete("/agenda/9999")
    assert resp.status_code == 404
