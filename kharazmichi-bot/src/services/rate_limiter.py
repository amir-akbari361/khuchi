"""
Rate limiting service to control message frequency.
"""

from typing import Optional, Tuple

from loguru import logger

from src.config import settings
from src.database.models import UsageLogCreate
from src.database.repositories import UsageLogRepository


class RateLimiter:
    """Service for rate limiting user messages."""

    def __init__(self, usage_repo: Optional[UsageLogRepository] = None):
        self.usage_repo = usage_repo or UsageLogRepository()
        self.limit = settings.rate_limit_per_day

    async def check_and_log(
        self,
        telegram_id: int,
        message_text: Optional[str] = None
    ) -> Tuple[bool, str, int]:
        """
        Check rate limit and log usage if allowed.
        
        Returns:
            Tuple of (is_allowed, message, remaining_count)
        """
        # Check current usage
        is_limited = await self.usage_repo.is_rate_limited(telegram_id)
        
        if is_limited:
            logger.warning(f"Rate limit exceeded for user {telegram_id}")
            return (
                False,
                f"⏰ شما به حد مجاز استفاده روزانه ({self.limit} پیام) رسیده‌اید.\n\nلطفاً فردا دوباره تلاش کنید.",
                0
            )

        # Log this usage
        await self.usage_repo.log_usage(
            UsageLogCreate(
                telegram_id=telegram_id,
                message_text=message_text[:500] if message_text else None
            )
        )

        # Get remaining count
        remaining = await self.usage_repo.get_remaining_messages(telegram_id)
        
        return True, "", remaining

    async def get_status(self, telegram_id: int) -> Tuple[int, int]:
        """
        Get rate limit status for a user.
        
        Returns:
            Tuple of (used_count, remaining_count)
        """
        used = await self.usage_repo.get_today_count(telegram_id)
        remaining = max(0, self.limit - used)
        return used, remaining
