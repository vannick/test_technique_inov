"""Factory FastAPI — enregistre les routes, middlewares et le seed au démarrage."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from src.config import get_settings
from src.db.database import init_db
from src.db.seed import seed_agenda
from src.routes import agenda, agent, health, session


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    logger.info(
        f"Démarrage — calendar_backend={settings.calendar_backend}, "
        f"log_level={settings.log_level}"
    )
    # Toujours initialiser la DB: elle porte aussi la mémoire de session,
    # même quand l'agenda est servi par CalDAV.
    init_db()
    # Le seed passe par la factory CalendarRepository et peuple donc
    # le backend actif (SQLite ou CalDAV) de façon idempotente.
    seed_agenda()
    yield
    logger.info("Arrêt de l'application")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Assistante de direction (INOVIE) - Backend IA",
        description=(
            "API d'un agent IA (tool calling) capable de gérer un agenda "
            "et de synthétiser des documents, avec mémoire de session."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(agent.router)
    app.include_router(agenda.router)
    app.include_router(session.router)
    app.include_router(health.router)
    return app
