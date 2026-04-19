"""Tests de l'authentification par clé API (header X-API-Key).

Par défaut dans la suite de tests, `API_KEY` n'est pas configurée -> auth
désactivée (mode dev). On réactive ici explicitement via monkeypatch et on
vérifie les codes 401 (header manquant) et 403 (clé invalide), ainsi que
l'exemption de `/health`.
"""
from src.config import get_settings


def _enable_api_key(monkeypatch, key: str = "secret-test-key") -> str:
    settings = get_settings()
    monkeypatch.setattr(settings, "api_key", key)
    return key


def test_health_is_not_protected_even_when_api_key_enabled(client, monkeypatch):
    _enable_api_key(monkeypatch)
    resp = client.get("/health")
    assert resp.status_code == 200


def test_protected_route_returns_401_without_header(client, monkeypatch):
    _enable_api_key(monkeypatch)
    resp = client.get("/agenda")
    assert resp.status_code == 401
    assert "X-API-Key" in resp.json()["detail"]


def test_protected_route_returns_403_with_wrong_key(client, monkeypatch):
    _enable_api_key(monkeypatch, "expected-key")
    resp = client.get("/agenda", headers={"X-API-Key": "wrong-key"})
    assert resp.status_code == 403


def test_protected_route_accepts_valid_key(client, monkeypatch):
    key = _enable_api_key(monkeypatch)
    resp = client.get("/agenda", headers={"X-API-Key": key})
    assert resp.status_code == 200


def test_auth_disabled_when_api_key_unset(client, monkeypatch):
    """Sans clé côté serveur, les routes sont ouvertes (comportement actuel du dev)."""
    settings = get_settings()
    monkeypatch.setattr(settings, "api_key", "")
    resp = client.get("/agenda")
    assert resp.status_code == 200
