"""Configuration centralisée — chargée depuis les variables d'environnement."""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
   pass


@lru_cache
def get_settings() -> Settings:
    return Settings()
