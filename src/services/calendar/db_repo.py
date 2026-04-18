"""Implémentation du dépôt calendrier via SQLAlchemy."""
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import and_, select

from src.db import database as _database
from src.models.orm import Event
from src.models.schemas import EventOut
from src.services.calendar.base import CalendarRepository


def _session():
    return _database.SessionLocal()


def _to_out(ev: Event) -> EventOut:
    return EventOut(
        id=str(ev.id), title=ev.title, date=ev.date, time=ev.time,
        participants=ev.participants or "", notes=ev.notes or "",
    )


class DBCalendarRepository(CalendarRepository):
    def list_events(self, date: Optional[str] = None, range_: Optional[str] = None) -> list[EventOut]:
        with _session() as db:
            stmt = select(Event)
            if date:
                stmt = stmt.where(Event.date == date)
            elif range_ == "week":
                today = datetime.today().date()
                end = today + timedelta(days=7)
                stmt = stmt.where(and_(Event.date >= today.isoformat(), Event.date <= end.isoformat()))
            stmt = stmt.order_by(Event.date, Event.time)
            return [_to_out(ev) for ev in db.execute(stmt).scalars()]

    def create_event(self, title, date, time, participants="", notes="") -> EventOut:
        with _session() as db:
            ev = Event(title=title, date=date, time=time, participants=participants, notes=notes)
            db.add(ev)
            db.commit()
            db.refresh(ev)
            return _to_out(ev)

    def get_event(self, event_id: str) -> Optional[EventOut]:
        with _session() as db:
            ev = db.get(Event, int(event_id))
            return _to_out(ev) if ev else None

    def update_event(self, event_id: str, patch: dict) -> Optional[EventOut]:
        with _session() as db:
            ev = db.get(Event, int(event_id))
            if not ev:
                return None
            for k, v in patch.items():
                if v is not None and hasattr(ev, k):
                    setattr(ev, k, v)
            db.commit()
            db.refresh(ev)
            return _to_out(ev)

    def delete_event(self, event_id: str) -> bool:
        with _session() as db:
            ev = db.get(Event, int(event_id))
            if not ev:
                return False
            db.delete(ev)
            db.commit()
            return True
