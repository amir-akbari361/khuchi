"""
Pydantic models for database entities.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class UserBase(BaseModel):
    """Base user model."""
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    student_code: str


class UserCreate(UserBase):
    """Model for creating a new user."""
    pass


class User(UserBase):
    """Complete user model with database fields."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UsageLogCreate(BaseModel):
    """Model for creating a usage log entry."""
    telegram_id: int
    message_text: Optional[str] = None


class UsageLog(UsageLogCreate):
    """Complete usage log model."""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationMessage(BaseModel):
    """Model for a conversation message."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ConversationCreate(BaseModel):
    """Model for creating/updating conversation."""
    telegram_id: int
    messages: List[ConversationMessage]


class Conversation(ConversationCreate):
    """Complete conversation model."""
    id: int
    updated_at: datetime

    class Config:
        from_attributes = True


class KnowledgeChunk(BaseModel):
    """Model for a knowledge base chunk."""
    content: str
    metadata: dict = Field(default_factory=dict)
    embedding: Optional[List[float]] = None


class KnowledgeSearchResult(BaseModel):
    """Model for knowledge search results."""
    content: str
    metadata: dict
    similarity: float
