"""
Authentication service for user management.
"""

from typing import Optional, Tuple

from loguru import logger

from src.database.models import User, UserCreate
from src.database.repositories import UserRepository


class AuthService:
    """Service for user authentication and registration."""

    def __init__(self, user_repo: Optional[UserRepository] = None):
        self.user_repo = user_repo or UserRepository()

    async def is_authenticated(self, telegram_id: int) -> bool:
        """Check if user is registered."""
        return await self.user_repo.exists(telegram_id)

    async def get_user(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID."""
        return await self.user_repo.get_by_telegram_id(telegram_id)

    async def register_user(
        self,
        telegram_id: int,
        student_code: str,
        username: Optional[str] = None,
        first_name: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Register a new user.
        
        Returns:
            Tuple of (success, message)
        """
        # Check if this Telegram account is already registered
        existing_user = await self.user_repo.get_by_telegram_id(telegram_id)
        if existing_user:
            return False, "شما قبلاً ثبت‌نام کرده‌اید! 🎓\n\n─────\n\nYou are already registered! 🎓"

        # Check if student code is already used by another account
        existing_student = await self.user_repo.get_by_student_code(student_code)
        if existing_student:
            return False, "❌ این شماره دانشجویی قبلاً با یک حساب دیگر ثبت شده!\n\nاگر این شماره متعلق به شماست و مشکلی دارید، با پشتیبانی تماس بگیرید.\n\n─────\n\n❌ This student ID is already registered with another account!\n\nIf this is your ID and you have issues, please contact support."

        # Validate student code format
        is_valid, validation_msg = self._validate_student_code(student_code)
        if not is_valid:
            return False, validation_msg

        # Create user
        user_data = UserCreate(
            telegram_id=telegram_id,
            student_code=student_code,
            username=username,
            first_name=first_name
        )

        user = await self.user_repo.create(user_data)
        if user:
            logger.info(f"New user registered: {telegram_id} - {student_code}")
            return True, f"✅ ثبت‌نام موفقیت‌آمیز بود!\n\nکد دانشجویی شما ({student_code}) با موفقیت ثبت شد. حالا می‌تونید از من هر سوالی درباره دانشگاه خوارزمی بپرسید! 🎓\n\n─────\n\n✅ Registration successful!\n\nYour student ID ({student_code}) has been registered. Now you can ask me anything about Kharazmi University! 🎓\n\nYou can ask in English or Persian!"
        
        return False, "❌ خطا در ثبت‌نام. لطفاً دوباره تلاش کنید.\n\n─────\n\n❌ Registration error. Please try again."

    def _validate_student_code(self, student_code: str) -> Tuple[bool, str]:
        """
        Validate student code format.
        
        Student codes should be numeric and have a reasonable length.
        Customize this based on your university's format.
        """
        if not student_code:
            return False, "❌ لطفاً کد دانشجویی خود را وارد کنید.\n\nمثال: /login 4022020030\n\n─────\n\n❌ Please enter your student ID.\n\nExample: /login 4022020030"

        # Remove any spaces
        student_code = student_code.strip()

        # Check if numeric
        if not student_code.isdigit():
            return False, "❌ کد دانشجویی باید فقط شامل اعداد باشد.\n\nمثال: /login 4022020030\n\n─────\n\n❌ Student ID must contain only numbers.\n\nExample: /login 4022020030"

        # Check length (adjust based on your university)
        if len(student_code) < 5:
            return False, "❌ کد دانشجویی وارد شده کوتاه است.\n\nمثال: /login 4022020030\n\n─────\n\n❌ Student ID is too short.\n\nExample: /login 4022020030"

        if len(student_code) > 15:
            return False, "❌ کد دانشجویی وارد شده خیلی طولانی است.\n\nمثال: /login 4022020030\n\n─────\n\n❌ Student ID is too long.\n\nExample: /login 4022020030"

        return True, ""

    def parse_login_command(self, message_text: str) -> Optional[str]:
        """
        Parse student code from /login command.
        
        Expected format: /login STUDENT_CODE
        """
        if not message_text:
            return None

        parts = message_text.strip().split()
        if len(parts) < 2:
            return None

        return parts[1].strip()
