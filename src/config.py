"""Configuration centralisée — chargée depuis les variables d'environnement."""
from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Paramètres applicatifs, chargés depuis `.env` ou l'environnement système."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    #LLM
    llm_api_key: str = Field(default="", alias="GROQ_API_KEY")
    llm_model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")

    # Base de données
    database_url: str = Field(
        default="sqlite:///./data/app.db", alias="DATABASE_URL"
    )

    # Backend calendrier: "db" (SQLAlchemy local) ou "caldav" (serveur externe)
    calendar_backend: Literal["db", "caldav"] = Field(
        default="db", alias="CALENDAR_BACKEND"
    )

    # CalDAV (utilisé si calendar_backend=caldav)
    caldav_url: Optional[str] = Field(default=None, alias="CALDAV_URL")
    caldav_username: Optional[str] = Field(default=None, alias="CALDAV_USERNAME")
    caldav_password: Optional[str] = Field(default=None, alias="CALDAV_PASSWORD")
    caldav_calendar_name: Optional[str] = Field(
        default=None, alias="CALDAV_CALENDAR_NAME"
    )

    # API
    api_key: Optional[str] = Field(default=None, alias="API_KEY")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


@lru_cache
def get_settings() -> Settings:
    return Settings()
