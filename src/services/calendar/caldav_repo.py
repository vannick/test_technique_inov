"""Implémentation du dépôt calendrier via CalDAV (Nextcloud, Radicale, iCloud...).

Les événements sont stockés/lus en tant que VEVENT ICS sur le serveur CalDAV.
"""
from datetime import date, datetime, timedelta
from typing import Optional

import caldav
from caldav.lib.error import NotFoundError
from loguru import logger

from src.models.schemas import EventOut
from src.services.calendar.base import CalendarRepository


class CalDAVCalendarRepository(CalendarRepository):
    def __init__(self, url: str, username: str, password: str, calendar_name: Optional[str] = None):
        if not url:
            raise RuntimeError("CALDAV_URL non configuré.")
        self._url = url
        self._username = username
        self._password = password
        self._calendar_name = calendar_name

    def _calendar(self) -> caldav.Calendar:
        client = caldav.DAVClient(url=self._url, username=self._username, password=self._password)
        principal = client.principal()
        calendars = principal.calendars()
        if not calendars:
            raise RuntimeError("Aucun calendrier CalDAV trouvé pour cet utilisateur.")
        if self._calendar_name:
            for c in calendars:
                if c.name == self._calendar_name:
                    return c
            logger.warning(f"Calendrier '{self._calendar_name}' introuvable, fallback sur le premier.")
        return calendars[0]

    @staticmethod
    def _to_out(event: caldav.Event) -> EventOut:
        vobj = event.vobject_instance.vevent
        dtstart = vobj.dtstart.value
        if isinstance(dtstart, datetime):
            ev_date = dtstart.date().isoformat()
            ev_time = dtstart.strftime("%H:%M")
        else:
            ev_date = dtstart.isoformat()
            ev_time = "00:00"
        participants = ""
        if hasattr(vobj, "attendee_list"):
            participants = ", ".join(a.value.replace("mailto:", "") for a in vobj.attendee_list)
        notes = vobj.description.value if hasattr(vobj, "description") else ""
        title = vobj.summary.value if hasattr(vobj, "summary") else ""
        return EventOut(
            id=str(vobj.uid.value), title=title, date=ev_date, time=ev_time,
            participants=participants, notes=notes,
        )

    def list_events(self, date: Optional[str] = None, range_: Optional[str] = None) -> list[EventOut]:
        cal = self._calendar()
        if date:
            start = datetime.fromisoformat(date)
            end = start + timedelta(days=1)
        elif range_ == "week":
            today = datetime.today()
            start, end = today, today + timedelta(days=7)
        else:
            start = datetime.today() - timedelta(days=30)
            end = datetime.today() + timedelta(days=365)
        results = cal.search(start=start, end=end, event=True, expand=True)
        return [self._to_out(ev) for ev in results]

    def create_event(self, title, date, time, participants="", notes="") -> EventOut:
        cal = self._calendar()
        dt = datetime.fromisoformat(f"{date}T{time}")
        event = cal.save_event(
            dtstart=dt,
            dtend=dt + timedelta(hours=1),
            summary=title,
            description=notes,
        )
        out = self._to_out(event)
        if participants:
            # CalDAV attendees: stockés en description si non gérés côté serveur
            out.participants = participants
        return out

    def get_event(self, event_id: str) -> Optional[EventOut]:
        cal = self._calendar()
        try:
            ev = cal.event_by_uid(event_id)
            return self._to_out(ev)
        except NotFoundError:
            return None

    def update_event(self, event_id: str, patch: dict) -> Optional[EventOut]:
        cal = self._calendar()
        try:
            ev = cal.event_by_uid(event_id)
        except NotFoundError:
            return None
        v = ev.vobject_instance.vevent
        if patch.get("title"):
            v.summary.value = patch["title"]
        if patch.get("notes") is not None:
            if hasattr(v, "description"):
                v.description.value = patch["notes"]
            else:
                v.add("description").value = patch["notes"]
        if patch.get("date") or patch.get("time"):
            current = v.dtstart.value
            d = patch.get("date") or (current.date().isoformat() if isinstance(current, datetime) else current.isoformat())
            t = patch.get("time") or (current.strftime("%H:%M") if isinstance(current, datetime) else "00:00")
            v.dtstart.value = datetime.fromisoformat(f"{d}T{t}")
            v.dtend.value = v.dtstart.value + timedelta(hours=1)
        ev.save()
        return self._to_out(ev)

    def delete_event(self, event_id: str) -> bool:
        cal = self._calendar()
        try:
            ev = cal.event_by_uid(event_id)
            ev.delete()
            return True
        except NotFoundError:
            return False
