"""Factory FastAPI — enregistre les routes, middlewares et le seed au démarrage."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from src.config import get_settings
from src.db.database import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    logger.info(f"Démarrage — backend calendrier: {settings.calendar_backend}")
    init_db()
    
def create_app() -> FastAPI:
    app = FastAPI(
        title="Assistant de direction — Backend IA",
        description=(
            "API d'un agent IA (tool calling) capable de gérer un agenda et "
            "de synthétiser des documents, avec mémoire de session."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    return app
