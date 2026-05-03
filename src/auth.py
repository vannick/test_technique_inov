"""Services d'authentification : hashage mots de passe, JWT, login/logout.

Utilise bcrypt pour stocker les mots de passe et PyJWT pour générer des access
tokens JWT (valide 24h). Le token contient l'identifiant utilisateur (`sub`)
et l'email.
"""
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
import jwt
from loguru import logger

from src.config import get_settings


def hash_password(password: str) -> str:
    """Hash un mot de passe en clair avec bcrypt (salt généré automatiquement)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Vérifie qu'un mot de passe en clair correspond au hash stocké."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(email: str, user_id: str) -> str:
    """Génère un JWT valable 24h contenant email + user_id."""
    settings = get_settings()
    expire = datetime.utcnow() + timedelta(hours=24)
    payload = {"sub": user_id, "email": email, "exp": expire}
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return token


def decode_access_token(token: str) -> Optional[dict]:
    """Décode et valide un JWT ; renvoie le payload ou None si invalide."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token expiré")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Token invalide: {e}")
        return None


def authenticate_user(email: str, password: str) -> Optional[dict]:
    """Vérifie les identifiants et renvoie les infos utilisateur si OK.

    Retourne `{"id": ..., "email": ...}` ou `None` en cas d'échec.
    """
    from src.db.database import SessionLocal
    from src.models.orm import User

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return {"id": user.id, "email": user.email}
