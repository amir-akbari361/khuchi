"""
Supabase client singleton for database operations.
"""

from functools import lru_cache
from typing import Optional

from supabase import Client, create_client
from loguru import logger

from src.config import settings


class SupabaseClient:
    """Singleton wrapper for Supabase client."""

    _instance: Optional[Client] = None

    @classmethod
    def get_client(cls) -> Client:
        """Get or create Supabase client instance."""
        if cls._instance is None:
            logger.info("Initializing Supabase client...")
            cls._instance = create_client(
                settings.supabase_url,
                settings.supabase_key
            )
            logger.info("Supabase client initialized successfully")
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the client instance (useful for testing)."""
        cls._instance = None


@lru_cache()
def get_supabase() -> Client:
    """Get cached Supabase client."""
    return SupabaseClient.get_client()


# Convenience access
supabase = get_supabase()
