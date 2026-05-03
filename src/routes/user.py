"""Routes utilisateur - profil et informations."""
from fastapi import APIRouter, Depends, HTTPException

from src.models.schemas import UserOut
from src.security import get_current_user
from src.db.database import SessionLocal
from src.models.orm import User

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/me", response_model=UserOut, summary="Informations de l'utilisateur connecté")
def get_current_user_info(current_user: dict = Depends(get_current_user)) -> UserOut:
    """Retourne les informations complètes de l'utilisateur authentifié."""
    with SessionLocal() as db:
        user = db.query(User).filter(User.id == current_user["sub"]).first()
        if not user:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
        return UserOut(
            id=str(user.id),
            email=user.email,
            role=user.role,
            nom=user.nom,
            prenom=user.prenom,
            adresse=user.adresse,
            created_at=user.created_at,
        )
