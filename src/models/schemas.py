"""Schémas Pydantic pour les routes FastAPI."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, EmailStr
from uuid import UUID

class EventIn(BaseModel):
    title: str
    date: str = Field(..., description="Format ISO YYYY-MM-DD")
    time: str = Field(..., description="Format HH:MM")
    participants: str = ""
    notes: str = ""


class EventPatch(BaseModel):
    title: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    participants: Optional[str] = None
    notes: Optional[str] = None


class EventOut(BaseModel):
    id: str
    title: str
    date: str
    time: str
    participants: str
    notes: str
    user_id: str = ""


class ChatIn(BaseModel):
    session_id: Optional[UUID] = Field(
        default=None,
        description="UUID de session existante. Laisser null au premier appel: le serveur en génère un.",
    )
    message: str


class ChatOut(BaseModel):
    session_id: UUID
    response: str
    tool_used: Optional[str] = None
    turn: int


class MessageOut(BaseModel):
    role: str
    content: str
    timestamp: datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str


class UserOut(BaseModel):
    id: str
    email: str
    role: str
    nom: Optional[str] = None
    prenom: Optional[str] = None
    adresse: Optional[str] = None
    created_at: datetime
