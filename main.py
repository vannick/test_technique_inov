"""Point d'entrée applicatif — lancé via `uvicorn main:app --reload`."""
from src.app import create_app

app = create_app()
