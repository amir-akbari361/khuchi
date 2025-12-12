"""
Configuration module for Kharazmichi Bot.
Uses pydantic-settings for type-safe configuration management.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Find project root (where .env is located)
PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Telegram Configuration
    telegram_bot_token: str = Field(..., description="Telegram bot token from BotFather")
    telegram_webhook_url: Optional[str] = Field(None, description="Webhook URL for production")

    # OpenAI Configuration
    openai_api_key: str = Field(..., description="OpenAI API key")

    # Supabase Configuration
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_key: str = Field(..., description="Supabase service role key")

    # Bot Configuration
    bot_name: str = Field(default="خوارزمی‌چی", description="Bot display name")
    rate_limit_per_day: int = Field(default=20, ge=1, le=1000, description="Max messages per user per day")
    conversation_memory_size: int = Field(default=5, ge=1, le=50, description="Number of messages to remember")

    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, ge=1, le=65535, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    # Admin Configuration
    admin_telegram_ids: Optional[str] = Field(default=None, description="Admin Telegram IDs (comma-separated)")

    def get_admin_ids(self) -> List[int]:
        """Get parsed admin IDs as list."""
        if not self.admin_telegram_ids or not self.admin_telegram_ids.strip():
            return []
        return [int(x.strip()) for x in self.admin_telegram_ids.split(",") if x.strip()]

    @property
    def is_webhook_mode(self) -> bool:
        """Check if bot should run in webhook mode."""
        return bool(self.telegram_webhook_url)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience access
settings = get_settings()
