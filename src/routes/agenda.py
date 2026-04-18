
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Response

from src.models.schemas import EventIn, EventOut, EventPatch
from src.services.calendar import get_calendar_repository

router = APIRouter(prefix="/agenda", tags=["agenda"])


@router.get("", response_model=list[EventOut])
def list_events(
    date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    range: Optional[str] = Query(None, description="week"),
):
    return get_calendar_repository().list_events(date=date, range_=range)


@router.post("", response_model=EventOut, status_code=201)
def create_event(payload: EventIn):
    return get_calendar_repository().create_event(**payload.model_dump())


@router.patch("/{event_id}", response_model=EventOut)
def patch_event(event_id: str, patch: EventPatch):
    result = get_calendar_repository().update_event(event_id, patch.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(status_code=404, detail="Événement introuvable")
    return result


@router.delete("/{event_id}", status_code=204)
def delete_event(event_id: str):
    ok = get_calendar_repository().delete_event(event_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Événement introuvable")
    return Response(status_code=204)
