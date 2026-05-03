"""Routes d'authentification : login (POST /auth/login).

Seule route non protégée. En cas de succès, renvoie un access token JWT
valable 24h. Les autres routes sont protégées via la dépendance `get_current_user`.
"""
from fastapi import APIRouter, HTTPException, status
from loguru import logger

from src.auth import authenticate_user, create_access_token
from src.models.schemas import LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse, summary="Se connecter")
def login(payload: LoginRequest) -> LoginResponse:
    """Authentifie un utilisateur via email/mot de passe et renvoie un JWT.

    - `401` si email inconnu ou mot de passe incorrect.
    - Le token est valable 24h.
    """
    user = authenticate_user(payload.email, payload.password)
    if not user:
        logger.warning(f"Échec login pour email={payload.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe invalide",
        )
    token = create_access_token(email=user["email"], user_id=user["id"])
    logger.info(f"Login réussi pour email={payload.email}")
    return LoginResponse(access_token=token, token_type="bearer", email=user["email"])
