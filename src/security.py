"""Authentification par JWT Bearer token.

Dépendance FastAPI `get_current_user` qui extrait et valide le token JWT
depuis le header `Authorization: Bearer <token>`. Le token doit être signé
avec `settings.jwt_secret` et contenir `sub` (user_id) + `email`.

Comportement:
- Token manquant ou invalide → 401.
- Token expiré → 401.
- En cas de succès, injecte le payload (dict) dans la route.
"""
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.auth import decode_access_token

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(security)]
) -> dict:
    """Valide le token JWT et renvoie le payload (sub, email, exp).

    Lève 401 si token absent, invalide ou expiré.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token d'accès manquant",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload
