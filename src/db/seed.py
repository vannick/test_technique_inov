"""Seed de l'agenda — 5 événements relatifs à la date courante.

Backend-agnostic: passe par `CalendarRepository` pour insérer les événements,
donc peuple aussi bien la base SQLite que le calendrier CalDAV actif.
Idempotent via un marqueur inclus dans les notes.
"""
from datetime import date, timedelta

from loguru import logger

from src.services.calendar import get_calendar_repository

SEED_MARKER = "[seed]"

SEED_EVENTS = [
    {"offset": 1, "title": "Comité de direction", "time": "09:00",
     "participants": "DG, DAF, DSI", "notes": "Budget Q2 à valider"},
    {"offset": 1, "title": "Réunion équipe Tech", "time": "14:30",
     "participants": "Lead Dev, DevOps", "notes": "Point sprint en cours"},
    {"offset": 2, "title": "Call client Ministère", "time": "11:00",
     "participants": "Client, Chef de projet", "notes": "Revue livrables phase 2"},
    {"offset": 3, "title": "Déjeuner partenaire", "time": "12:30",
     "participants": "Partenaire externe", "notes": "Hôtel Hilton Yaoundé"},
    {"offset": 4, "title": "Revue RH mensuelle", "time": "10:00",
     "participants": "DRH, Managers", "notes": "Évaluations semestrielles"},
]


def seed_agenda() -> None:
    """Insère les événements de départ si le calendrier actif est vide de seeds.

    La détection s'appuie sur le marqueur `[seed]` présent dans les notes:
    le seed ne se re-déclenche pas quand on relance l'app.
    """
    try:
        repo = get_calendar_repository()
        existing = repo.list_events()
    except Exception as e:  # noqa: BLE001
        # Serveur CalDAV indisponible au démarrage: on saute le seed sans planter l'app.
        logger.warning(f"Seed ignoré — backend calendrier inaccessible: {e}")
        return

    if any(SEED_MARKER in (ev.notes or "") for ev in existing):
        logger.info("Seed ignoré — agenda déjà peuplé (marqueur détecté).")
        return

    today = date.today()
    created = 0
    for item in SEED_EVENTS:
        try:
            repo.create_event(
                title=item["title"],
                date=(today + timedelta(days=item["offset"])).isoformat(),
                time=item["time"],
                participants=item["participants"],
                notes=f"{item['notes']} {SEED_MARKER}",
            )
            created += 1
        except Exception as e:  # noqa: BLE001
            logger.exception(f"Seed: échec création '{item['title']}': {e}")
    logger.info(f"Seed agenda: {created}/{len(SEED_EVENTS)} événements insérés.")
