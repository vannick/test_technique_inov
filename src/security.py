"""Authentification par clé API via header HTTP.

Mise en place d'une dépendance FastAPI `require_api_key` qui exige un header
`X-API-Key` égal à `settings.api_key` sur les routes protégées.

Comportement:
- Si `settings.api_key` est vide/None: l'auth est *désactivée* (mode dev).
- Sinon: header manquant -> 401, header incorrect -> 403.
- Le nom du header est déclaré via `APIKeyHeader`, ce qui ajoute automatiquement
  le bouton "Authorize" dans Swagger UI.
"""
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from src.config import get_settings

API_KEY_HEADER = "X-API-Key"

_api_key_scheme = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)


def require_api_key(provided: str | None = Security(_api_key_scheme)) -> None:
    """Valide le header `X-API-Key` contre `settings.api_key`.

    Noop si `api_key` n'est pas configurée côté serveur (pratique en dev).
    """
    expected = get_settings().api_key
    if not expected:
        return
    if provided is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Header {API_KEY_HEADER} manquant",
        )
    if provided != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clé API invalide",
        )
