"""Configuration partagée des tests.

- Force un environnement isolé (backend DB, SQLite dans un fichier temporaire,
  clé LLM factice) avant toute importation du package `src`.
- Fournit un client FastAPI et une base de données réinitialisée entre tests.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

# IMPORTANT: positionner ces env vars AVANT d'importer quoi que ce soit de `src`.
_TEST_DIR = Path(tempfile.mkdtemp(prefix="inov_test_"))
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DIR}/test.db"
os.environ["CALENDAR_BACKEND"] = "db"
os.environ["LLM_API_KEY"] = "test-key-not-used"
os.environ["LOG_LEVEL"] = "WARNING"
# Désactive l'auth par clé API dans la suite par défaut. Les tests qui
# veulent la vérifier l'activent explicitement via monkeypatch.
os.environ["API_KEY"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from src.app import create_app  # noqa: E402
from src.config import get_settings  # noqa: E402
from src.db.database import Base, engine  # noqa: E402
from src.models.orm import User  # noqa: E402  # ensure model is registered


@pytest.fixture(autouse=True)
def _reset_db():
    """Drop + recreate les tables avant chaque test pour garantir l'isolation."""
    # Assurer que le cache des settings est bien neutre pour les tests.
    get_settings.cache_clear()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def app():
    """Instance FastAPI prête à l'emploi (sans exécution du lifespan/seed)."""
    return create_app()


@pytest.fixture
def client(app):
    """Client HTTP in-process.

    N.B.: on n'utilise PAS `with TestClient(app)` afin d'éviter de déclencher
    le seed au démarrage (chaque test part d'une DB vide).
    """
    return TestClient(app)


@pytest.fixture
def auth_headers(client: TestClient):
    """Crée un utilisateur de test et renvoie les headers Authorization."""
    from src.auth import hash_password
    from src.db.database import SessionLocal
    from src.models.orm import User

    hashed = hash_password("secret")
    user = User(email="alice@example.com", password_hash=hashed)
    with SessionLocal() as db:
        db.add(user)
        db.commit()
        db.refresh(user)

    resp = client.post("/auth/login", json={"email": "alice@example.com", "password": "secret"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
