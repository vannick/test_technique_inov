"""Factory: renvoie l'implémentation CalendarRepository selon CALENDAR_BACKEND."""
from src.config import get_settings
from src.services.calendar.base import CalendarRepository
from src.services.calendar.caldav_repo import CalDAVCalendarRepository
from src.services.calendar.db_repo import DBCalendarRepository


def get_calendar_repository() -> CalendarRepository:
    settings = get_settings()
    if settings.calendar_backend == "caldav":
        return CalDAVCalendarRepository(
            url=settings.caldav_url or "",
            username=settings.caldav_username or "",
            password=settings.caldav_password or "",
            calendar_name=settings.caldav_calendar_name,
        )
    return DBCalendarRepository()
