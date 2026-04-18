"""Factory FastAPI — enregistre les routes, middlewares et le seed au démarrage."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from src.config import get_settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    logger.info(
        f"Démarrage — calendar_backend={settings.calendar_backend}, "
        f"log_level={settings.log_level}"
    )
    yield
    logger.info("Arrêt de l'application")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Assistante de direction (INOVIE) - Backend IA",
        description=(
            "API d'un agent IA (tool calling) capable de gérer un agenda"
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.get("/health", tags=["health"])
    def health() -> dict:
        """Endpoint de santé minimal """
        settings = get_settings()
        return {
            "status": "ok",
            "calendar_backend": settings.calendar_backend,
        }

    return app
