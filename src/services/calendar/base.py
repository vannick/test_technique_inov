"""Interface abstraite du dépôt calendrier — implémentée par DB ou CalDAV."""
from abc import ABC, abstractmethod
from typing import Optional

from src.models.schemas import EventOut


class CalendarRepository(ABC):
    @abstractmethod
    def list_events(self, date: Optional[str] = None, range_: Optional[str] = None, user_id: Optional[str] = None) -> list[EventOut]:
        ...

    @abstractmethod
    def create_event(
        self, title: str, date: str, time: str, participants: str = "", notes: str = "", user_id: Optional[str] = None
    ) -> EventOut:
        ...

    @abstractmethod
    def get_event(self, event_id: str) -> Optional[EventOut]:
        ...

    @abstractmethod
    def update_event(self, event_id: str, patch: dict) -> Optional[EventOut]:
        ...

    @abstractmethod
    def delete_event(self, event_id: str) -> bool:
        ...
