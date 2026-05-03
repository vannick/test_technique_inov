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


def test_create_event_returns_201_and_body(client, auth_headers):
    resp = client.post("/agenda", json=_event_payload(), headers=auth_headers)
    assert resp.status_code == 201
    ev = resp.json()
    assert ev["id"]
    assert ev["title"] == "Reunion test"
    assert ev["participants"] == "Alice, Bob"


def test_list_events_empty_by_default(client, auth_headers):
    resp = client.get("/agenda", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_events_after_create(client, auth_headers):
    payload = {"title": "Réunion", "date": "2026-01-01", "time": "10:00"}
    client.post("/agenda", json=payload, headers=auth_headers)
    resp = client.get("/agenda", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["title"] == "Réunion"


def test_patch_event_updates_fields(client, auth_headers):
    payload = {"title": "Réunion", "date": "2026-01-01", "time": "10:00"}
    create_resp = client.post("/agenda", json=payload, headers=auth_headers)
    event_id = create_resp.json()["id"]
    patch = {"title": "Titre modifié", "notes": "Nouvelles notes"}
    resp = client.patch(f"/agenda/{event_id}", json=patch, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Titre modifié"
    assert data["notes"] == "Nouvelles notes"


def test_filter_by_date(client, auth_headers):
    d1 = (date.today() + timedelta(days=1)).isoformat()
    d2 = (date.today() + timedelta(days=3)).isoformat()
    client.post("/agenda", json=_event_payload(title="J+1"), headers=auth_headers)
    client.post("/agenda", json=_event_payload(title="J+3", offset_days=3), headers=auth_headers)
    resp = client.get(f"/agenda?date={d1}", headers=auth_headers)
    data = resp.json()
    assert len(data) == 1
    assert data[0]["date"] == d1
    assert data[0]["title"] == "J+1"
    # Sanity: le second est bien dans la base à une autre date.
    resp2 = client.get(f"/agenda?date={d2}")
    assert len(resp2.json()) == 1


def test_filter_range_week(client, auth_headers):
    # J+2 inclus, J+10 exclu
    client.post("/agenda", json=_event_payload(title="proche", offset_days=2))
    client.post("/agenda", json=_event_payload(title="lointain", offset_days=10))
    resp = client.get("/agenda?range=week", headers=auth_headers)
    titles = [e["title"] for e in resp.json()]
    assert "proche" in titles
    assert "lointain" not in titles


def test_patch_event_updates_fields(client):
    created = client.post("/agenda", json=_event_payload(), headers=auth_headers).json()
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


def test_patch_unknown_event_returns_404(client, auth_headers):
    resp = client.patch("/agenda/9999", json={"title": "x"})
    assert resp.status_code == 404


def test_delete_event_returns_204(client, auth_headers):
    created = client.post("/agenda", json=_event_payload(), headers=auth_headers).json()
    resp = client.delete(f"/agenda/{created["id"]}", headers=auth_headers)
    assert resp.status_code == 204
    # Plus présent ensuite.
    assert client.get("/agenda", headers=auth_headers).json() == []


def test_delete_unknown_event_returns_404(client, auth_headers):
    resp = client.delete("/agenda/9999")
    assert resp.status_code == 404
