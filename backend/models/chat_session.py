"""
Chat Session model — persisted conversation history for AI chat.

Replaces the in-memory _sessions dict in chat_service.py.
Sessions auto-expire via MongoDB TTL index on updated_at (7 days).
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from datetime import datetime

from .common import generate_id, utc_now


class ChatSession(BaseModel):
    """A single AI chat conversation."""

    id: str = Field(default_factory=generate_id)
    organization_id: str
    session_id: str          # frontend-generated UUID (crypto.randomUUID())
    user_id: str             # audit: who owns this session
    messages: List[Dict[str, Any]] = []
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
