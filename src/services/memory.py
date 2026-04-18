"""Mémoire de session: persistance des échanges dans la DB."""
import uuid
from typing import Optional

from sqlalchemy import select

from src.db.database import SessionLocal
from src.models.orm import ChatSession, Message


def ensure_session(session_id: Optional[str]) -> str:
    """Retourne un id de session existant ou en crée un nouveau."""
    with SessionLocal() as db:
        if session_id:
            existing = db.get(ChatSession, session_id)
            if existing:
                return session_id
        new_id = session_id or str(uuid.uuid4())
        db.add(ChatSession(id=new_id))
        db.commit()
        return new_id


def add_message(session_id: str, role: str, content: str, tool_used: Optional[str] = None) -> None:
    with SessionLocal() as db:
        db.add(Message(session_id=session_id, role=role, content=content, tool_used=tool_used))
        db.commit()


def get_history(session_id: str) -> list[Message]:
    with SessionLocal() as db:
        stmt = select(Message).where(Message.session_id == session_id).order_by(Message.timestamp)
        return list(db.execute(stmt).scalars())


def get_turn_count(session_id: str) -> int:
    """Nombre d'échanges (messages user) dans la session."""
    with SessionLocal() as db:
        stmt = select(Message).where(
            Message.session_id == session_id, Message.role == "user"
        )
        return len(list(db.execute(stmt).scalars()))
