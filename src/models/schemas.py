"""Schémas Pydantic utilisés par les routes."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


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
    participants: str = ""
    notes: str = ""


class ChatIn(BaseModel):
    session_id: Optional[str] = None
    message: str


class ChatOut(BaseModel):
    session_id: str
    response: str
    tool_used: Optional[str] = None
    turn: int


class MessageOut(BaseModel):
    role: str
    content: str
    timestamp: datetime
