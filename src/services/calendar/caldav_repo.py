"""Implémentation du dépôt calendrier via CalDAV

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
    def __init__(
        self,
        url: str,
        username: str,
        password: str,
        calendar_name: Optional[str] = None,
        calendar_url: Optional[str] = None,
    ):
        if not url and not calendar_url:
            raise RuntimeError("CALDAV_URL (ou CALDAV_CALENDAR_URL) non configuré.")
        self._url = url
        self._username = username
        self._password = password
        self._calendar_name = calendar_name
        self._calendar_url = calendar_url

    def _client(self) -> caldav.DAVClient:
        # Le DAVClient a besoin d'une URL racine; on utilise l'URL de la collection
        # comme fallback si CALDAV_URL n'est pas défini.
        base = self._url or self._calendar_url
        return caldav.DAVClient(url=base, username=self._username, password=self._password)

    def _calendar(self) -> caldav.Calendar:
        """Résout la collection à utiliser selon la config du repo.

        Priorités: URL directe (self._calendar_url) > découverte via principal
        avec filtre optionnel par nom > première collection trouvée.
        """
        client = self._client()
        if self._calendar_url:
            return client.calendar(url=self._calendar_url)
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
    def _parse_participants(value: str) -> list[str]:
        """Découpe une chaîne 'X, Y, Z' en liste normalisée."""
        return [p.strip() for p in value.split(",") if p.strip()]

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
        # Participants: CN d'abord (nom lisible), sinon on retire 'mailto:' de la valeur.
        participants = ""
        if hasattr(vobj, "attendee_list"):
            parts: list[str] = []
            for a in vobj.attendee_list:
                cn = getattr(a, "params", {}).get("CN")
                if cn:
                    parts.append(cn[0] if isinstance(cn, list) else cn)
                else:
                    parts.append(str(a.value).replace("mailto:", ""))
            participants = ", ".join(parts)
        notes = vobj.description.value if hasattr(vobj, "description") else ""
        title = vobj.summary.value if hasattr(vobj, "summary") else ""
        return EventOut(
            id=str(vobj.uid.value), title=title, date=ev_date, time=ev_time,
            participants=participants, notes=notes,
        )

    @staticmethod
    def _set_attendees(vevent, participants: str) -> None:
        """Réécrit les propriétés ATTENDEE du VEVENT à partir d'une chaîne CSV.

        Chaque participant est stocké avec son nom lisible en paramètre CN et
        une valeur `mailto:<slug>@local` (placeholder si ce n'est pas un email).
        """
        # Supprime les attendees existants (pour les mises à jour).
        if hasattr(vevent, "attendee_list"):
            for a in list(vevent.attendee_list):
                vevent.remove(a)
        for name in CalDAVCalendarRepository._parse_participants(participants):
            att = vevent.add("attendee")
            if "@" in name:
                att.value = f"mailto:{name}"
            else:
                slug = name.lower().replace(" ", ".").replace(",", "")
                att.value = f"mailto:{slug}@local"
                att.params["CN"] = [name]

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
        if participants:
            # Ajoute les ATTENDEE après création, puis re-persiste le VEVENT.
            self._set_attendees(event.vobject_instance.vevent, participants)
            event.save()
        return self._to_out(event)

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
        if patch.get("participants") is not None:
            self._set_attendees(v, patch["participants"])
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
