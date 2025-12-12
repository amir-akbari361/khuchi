"""
Repository classes for database operations.
Implements the Repository pattern for clean data access.
"""

from datetime import datetime, timezone
from typing import List, Optional

from loguru import logger
from supabase import Client

from src.config import settings
from src.database.models import (
    User,
    UserCreate,
    UsageLog,
    UsageLogCreate,
    ConversationMessage,
    KnowledgeSearchResult,
)
from src.database.supabase_client import get_supabase


class UserRepository:
    """Repository for user operations."""

    def __init__(self, client: Optional[Client] = None):
        self.client = client or get_supabase()
        self.table = "users"

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID."""
        try:
            response = self.client.table(self.table).select("*").eq(
                "telegram_id", telegram_id
            ).execute()

            if response.data and len(response.data) > 0:
                return User(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error fetching user {telegram_id}: {e}")
            return None

    async def get_by_student_code(self, student_code: str) -> Optional[User]:
        """Get user by student code - to check for duplicates."""
        try:
            response = self.client.table(self.table).select("*").eq(
                "student_code", student_code
            ).execute()

            if response.data and len(response.data) > 0:
                return User(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error fetching user by student code {student_code}: {e}")
            return None

    async def create(self, user_data: UserCreate) -> Optional[User]:
        """Create a new user."""
        try:
            response = self.client.table(self.table).insert(
                user_data.model_dump()
            ).execute()

            if response.data and len(response.data) > 0:
                logger.info(f"Created user: {user_data.telegram_id}")
                return User(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None

    async def exists(self, telegram_id: int) -> bool:
        """Check if user exists."""
        user = await self.get_by_telegram_id(telegram_id)
        return user is not None


class UsageLogRepository:
    """Repository for usage log operations (rate limiting)."""

    def __init__(self, client: Optional[Client] = None):
        self.client = client or get_supabase()
        self.table = "usage_logs"

    async def get_today_count(self, telegram_id: int) -> int:
        """Get message count for today."""
        try:
            # Get start of today in UTC
            today_start = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            ).isoformat()

            response = self.client.table(self.table).select(
                "id", count="exact"
            ).eq(
                "telegram_id", telegram_id
            ).gte(
                "created_at", today_start
            ).execute()

            return response.count or 0
        except Exception as e:
            logger.error(f"Error getting usage count for {telegram_id}: {e}")
            return 0

    async def log_usage(self, log_data: UsageLogCreate) -> Optional[UsageLog]:
        """Log a message usage."""
        try:
            response = self.client.table(self.table).insert(
                log_data.model_dump()
            ).execute()

            if response.data and len(response.data) > 0:
                return UsageLog(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error logging usage: {e}")
            return None

    async def is_rate_limited(self, telegram_id: int) -> bool:
        """Check if user has exceeded rate limit."""
        count = await self.get_today_count(telegram_id)
        return count >= settings.rate_limit_per_day

    async def get_remaining_messages(self, telegram_id: int) -> int:
        """Get remaining messages for today."""
        count = await self.get_today_count(telegram_id)
        return max(0, settings.rate_limit_per_day - count)


class ConversationRepository:
    """Repository for conversation history (memory)."""

    def __init__(self, client: Optional[Client] = None):
        self.client = client or get_supabase()
        self.table = "conversations"

    async def get_messages(self, telegram_id: int) -> List[ConversationMessage]:
        """Get conversation history for a user."""
        try:
            response = self.client.table(self.table).select("*").eq(
                "telegram_id", telegram_id
            ).execute()

            if response.data and len(response.data) > 0:
                messages_data = response.data[0].get("messages", [])
                return [ConversationMessage(**msg) for msg in messages_data]
            return []
        except Exception as e:
            logger.error(f"Error fetching conversation for {telegram_id}: {e}")
            return []

    async def save_messages(
        self,
        telegram_id: int,
        messages: List[ConversationMessage]
    ) -> bool:
        """Save conversation history, keeping only recent messages."""
        try:
            # Keep only the most recent messages based on config
            recent_messages = messages[-settings.conversation_memory_size * 2:]
            messages_data = [msg.model_dump(mode="json") for msg in recent_messages]

            # Upsert: insert or update
            response = self.client.table(self.table).upsert(
                {
                    "telegram_id": telegram_id,
                    "messages": messages_data,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                },
                on_conflict="telegram_id"
            ).execute()

            return bool(response.data)
        except Exception as e:
            logger.error(f"Error saving conversation for {telegram_id}: {e}")
            return False

    async def add_message(
        self,
        telegram_id: int,
        role: str,
        content: str
    ) -> bool:
        """Add a single message to conversation history."""
        messages = await self.get_messages(telegram_id)
        messages.append(ConversationMessage(role=role, content=content))
        return await self.save_messages(telegram_id, messages)

    async def clear_history(self, telegram_id: int) -> bool:
        """Clear conversation history for a user."""
        try:
            self.client.table(self.table).delete().eq(
                "telegram_id", telegram_id
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Error clearing conversation for {telegram_id}: {e}")
            return False


class KnowledgeRepository:
    """Repository for knowledge base (vector store) operations."""

    def __init__(self, client: Optional[Client] = None):
        self.client = client or get_supabase()
        self.table = "knowledge_embeddings"

    async def search(
        self,
        query_embedding: List[float],
        limit: int = 5,
        similarity_threshold: float = 0.7
    ) -> List[KnowledgeSearchResult]:
        """Search for similar documents using vector similarity."""
        try:
            # Use Supabase RPC for vector similarity search
            response = self.client.rpc(
                "match_knowledge",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": similarity_threshold,
                    "match_count": limit
                }
            ).execute()

            if response.data:
                return [
                    KnowledgeSearchResult(
                        content=item["content"],
                        metadata=item.get("metadata", {}),
                        similarity=item["similarity"]
                    )
                    for item in response.data
                ]
            return []
        except Exception as e:
            logger.error(f"Error searching knowledge base: {e}")
            return []

    async def insert(
        self,
        content: str,
        embedding: List[float],
        metadata: dict = None
    ) -> bool:
        """Insert a new knowledge chunk."""
        try:
            response = self.client.table(self.table).insert({
                "content": content,
                "embedding": embedding,
                "metadata": metadata or {}
            }).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error inserting knowledge chunk: {e}")
            return False

    async def delete_all(self) -> bool:
        """Delete all knowledge chunks (for re-indexing)."""
        try:
            self.client.table(self.table).delete().neq("id", 0).execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting knowledge base: {e}")
            return False
