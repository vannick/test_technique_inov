"""Tests de l'authentification JWT : login, token invalide, routes protégées."""
import pytest
from fastapi.testclient import TestClient

from src.auth import hash_password
from src.db.database import SessionLocal
from src.models.orm import User


def _create_user(email: str = "alice@example.com", password: str = "secret") -> str:
    """Crée un utilisateur en DB et renvoie son ID."""
    hashed = hash_password(password)
    user = User(id="user-1", email=email, password_hash=hashed)
    with SessionLocal() as db:
        db.add(user)
        db.commit()
        db.refresh(user)
    return user.id


def test_login_success(client: TestClient):
    _create_user()
    resp = client.post("/auth/login", json={"email": "alice@example.com", "password": "secret"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["email"] == "alice@example.com"


def test_login_invalid_email(client: TestClient):
    resp = client.post("/auth/login", json={"email": "bob@example.com", "password": "secret"})
    assert resp.status_code == 401
    assert "Email ou mot de passe invalide" in resp.json()["detail"]


def test_login_invalid_password(client: TestClient):
    _create_user()
    resp = client.post("/auth/login", json={"email": "alice@example.com", "password": "wrong"})
    assert resp.status_code == 401


def test_protected_route_without_token(client: TestClient):
    resp = client.get("/agenda")
    assert resp.status_code == 401
    assert "Token d'accès manquant" in resp.json()["detail"]


def test_protected_route_with_invalid_token(client: TestClient):
    resp = client.get("/agenda", headers={"Authorization": "Bearer invalid-token"})
    assert resp.status_code == 401
    assert "Token invalide ou expiré" in resp.json()["detail"]


def test_protected_route_with_valid_token(client: TestClient):
    _create_user()
    login_resp = client.post("/auth/login", json={"email": "alice@example.com", "password": "secret"})
    token = login_resp.json()["access_token"]
    agenda_resp = client.get("/agenda", headers={"Authorization": f"Bearer {token}"})
    assert agenda_resp.status_code == 200


def test_health_open_without_token(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
