"""Routes CRUD de l'agenda. Le backend (DB ou CalDAV) est résolu via la factory."""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Response, Depends

from src.models.schemas import EventIn, EventOut, EventPatch
from src.security import get_current_user
from src.services.calendar import get_calendar_repository

router = APIRouter(prefix="/agenda", tags=["agenda"])


@router.get("", response_model=list[EventOut], summary="Lister les événements")
def list_events(
    date: Optional[str] = Query(None, description="Filtre date exacte au format YYYY-MM-DD"),
    range: Optional[str] = Query(None, description="Plage prédéfinie: 'week' = 7 prochains jours"),
    current_user: dict = Depends(get_current_user),
):
    """Renvoie tous les événements de l'utilisateur connecté, ou filtre par date précise ou par plage."""
    return get_calendar_repository().list_events(date=date, range_=range, user_id=current_user["sub"])


@router.post("", response_model=EventOut, status_code=201, summary="Créer un événement")
def create_event(payload: EventIn, current_user: dict = Depends(get_current_user)):
    """Crée un événement pour l'utilisateur connecté et renvoie sa représentation persistée (HTTP 201)."""
    return get_calendar_repository().create_event(**payload.model_dump(), user_id=current_user["sub"])


@router.patch("/{event_id}", response_model=EventOut, summary="Mettre à jour un événement")
def patch_event(event_id: str, patch: EventPatch, current_user: dict = Depends(get_current_user)):
    """Met à jour les champs fournis (les autres restent inchangés). 404 si introuvable."""
    result = get_calendar_repository().update_event(event_id, patch.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(status_code=404, detail="Événement introuvable")
    # Optionnel : vérifier que l'événement appartient à l'utilisateur
    if result.user_id != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Accès interdit à cet événement")
    return result


@router.delete("/{event_id}", status_code=204, summary="Supprimer un événement")
def delete_event(event_id: str, current_user: dict = Depends(get_current_user)):
    """Supprime l'événement (HTTP 204). Renvoie 404 si l'identifiant est inconnu."""
    # D'abord récupérer l'événement pour vérifier l'appartenance
    ev = get_calendar_repository().get_event(event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Événement introuvable")
    if ev.user_id != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Accès interdit à cet événement")
    if not get_calendar_repository().delete_event(event_id):
        raise HTTPException(status_code=404, detail="Événement introuvable")
    return Response(status_code=204)
