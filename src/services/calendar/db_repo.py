"""Implémentation du dépôt calendrier via SQLAlchemy."""
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_, select

from src.db.database import SessionLocal
from src.models.orm import Event
from src.models.schemas import EventOut
from src.services.calendar.base import CalendarRepository


def _session():
    return SessionLocal()


def _to_out(ev: Event) -> EventOut:
    # Convertit le datetime `start` en date+time pour compatibilité avec les schémas legacy
    # start peut être string ou datetime selon la provenance
    start_dt = ev.start
    if isinstance(start_dt, str):
        start_dt = datetime.fromisoformat(start_dt)
    elif not isinstance(start_dt, datetime):
        raise TypeError(f"Event.start doit être datetime ou str, reçu {type(start_dt)}")
    return EventOut(
        id=str(ev.id),
        title=ev.title,
        date=start_dt.date().isoformat(),
        time=start_dt.time().isoformat()[:5],
        participants=ev.participants or "",
        notes=ev.notes or "",
        user_id=str(ev.user_id),
    )


class DBCalendarRepository(CalendarRepository):
    def list_events(self, date: Optional[str] = None, range_: Optional[str] = None, user_id: Optional[str] = None) -> list[EventOut]:
        with _session() as db:
            stmt = select(Event)
            if date:
                stmt = stmt.where(Event.start.startswith(date))
            elif range_ == "week":
                today = datetime.today().date()
                end = today + timedelta(days=7)
                stmt = stmt.where(and_(Event.start >= today.isoformat(), Event.start <= end.isoformat()))
            if user_id:
                stmt = stmt.where(Event.user_id == user_id)
            stmt = stmt.order_by(Event.start)
            return [_to_out(ev) for ev in db.execute(stmt).scalars()]

    def create_event(self, title, date, time, participants="", notes="", user_id=None) -> EventOut:
        with _session() as db:
            start_dt = datetime.fromisoformat(f"{date}T{time}:00")
            ev = Event(title=title, start=start_dt, end=start_dt, participants=participants, notes=notes, user_id=user_id)
            db.add(ev)
            db.commit()
            db.refresh(ev)
            return _to_out(ev)

    def get_event(self, event_id: str) -> Optional[EventOut]:
        with _session() as db:
            ev = db.get(Event, event_id)
            return _to_out(ev) if ev else None

    def update_event(self, event_id: str, patch: dict) -> Optional[EventOut]:
        with _session() as db:
            ev = db.get(Event, event_id)
            if not ev:
                return None
            # Gérer le cas où date/time sont fournis séparément -> recomposer start/end
            if "date" in patch or "time" in patch:
                existing = ev.start
                new_date = patch.get("date", existing.date().isoformat())
                new_time = patch.get("time", existing.time().isoformat()[:5])
                ev.start = datetime.fromisoformat(f"{new_date}T{new_time}:00")
                ev.end = ev.start
            for k, v in patch.items():
                if k in ("date", "time"):
                    continue
                if v is not None and hasattr(ev, k):
                    setattr(ev, k, v)
            db.commit()
            db.refresh(ev)
            return _to_out(ev)

    def delete_event(self, event_id: str) -> bool:
        with _session() as db:
            ev = db.get(Event, event_id)
            if not ev:
                return False
            db.delete(ev)
            db.commit()
            return True
