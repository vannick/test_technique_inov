"""Tests du seed d'agenda (idempotence via le marqueur)."""
from src.db.seed import SEED_EVENTS, SEED_MARKER, seed_agenda
from src.services.calendar import get_calendar_repository


def test_seed_inserts_all_events_on_empty_calendar():
    repo = get_calendar_repository()
    assert repo.list_events() == []
    seed_agenda()
    events = repo.list_events()
    assert len(events) == len(SEED_EVENTS)
    # Le marqueur est présent dans les notes de chaque event seed.
    assert all(SEED_MARKER in e.notes for e in events)


def test_seed_is_idempotent():
    seed_agenda()
    first = get_calendar_repository().list_events()
    seed_agenda()  # ne doit rien insérer de plus
    second = get_calendar_repository().list_events()
    assert len(first) == len(second) == len(SEED_EVENTS)


def test_seed_skipped_when_marker_absent_but_events_present_without_seed_marker():
    """Cas limite: l'utilisateur a ses propres events sans marqueur.
    Le seed doit malgré tout s'exécuter et ajouter ses entrées marquées.
    """
    repo = get_calendar_repository()
    repo.create_event(
        title="Event perso", date="2099-01-01", time="09:00",
        participants="", notes="sans marqueur",
    )
    seed_agenda()
    events = repo.list_events()
    marked = [e for e in events if SEED_MARKER in e.notes]
    assert len(marked) == len(SEED_EVENTS)
    assert len(events) == len(SEED_EVENTS) + 1
