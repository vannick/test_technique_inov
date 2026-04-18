"""Seed de l'agenda — 5 événements relatifs à la date courante."""
from datetime import date, timedelta

from loguru import logger

from src.db.database import SessionLocal
from src.models.orm import Event

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
    """Insère les événements de départ si la table est vide."""
    db = SessionLocal()
    try:
        if db.query(Event).count() > 0:
            logger.info("Seed ignoré — agenda déjà peuplé.")
            return
        today = date.today()
        for item in SEED_EVENTS:
            ev = Event(
                title=item["title"],
                date=(today + timedelta(days=item["offset"])).isoformat(),
                time=item["time"],
                participants=item["participants"],
                notes=item["notes"],
            )
            db.add(ev)
        db.commit()
        logger.info(f"Seed agenda: {len(SEED_EVENTS)} événements insérés.")
    finally:
        db.close()
