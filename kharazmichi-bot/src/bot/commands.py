"""
Telegram command handlers (/start, /login, /help, etc.)
"""

from telegram import Update
from telegram.ext import ContextTypes

from loguru import logger

from src.services.auth import AuthService
from src.services.rate_limiter import RateLimiter


# Response messages - Bilingual (Persian/English)
MESSAGES_FA = {
    "welcome": """سلام {name}! 👋

من **خوارزمی‌چی** هستم 🤖 - دستیار هوشمند دانشگاه خوارزمی!

هرچی راجع به دانشگاه خوارزمی بخوای، بپرس! از لوکیشن دانشکده‌ها گرفته تا اطلاعات رشته‌ها و خدمات دانشگاه.

⚠️ برای استفاده، ابتدا باید با کد دانشجویی ثبت‌نام کنی:

👈 /login کد_دانشجویی

مثال: `/login 4023030011`

🌍 International students: Type /help_en for English""",

    "help": """📚 **راهنمای خوارزمی‌چی**

🔹 **دستورات:**
• /start - شروع گفتگو
• /login کد_دانشجویی - ثبت‌نام با کد دانشجویی
• /help - راهنما (فارسی)
• /help_en - راهنما (English)
• /status - وضعیت اکانت و پیام‌های باقی‌مانده

🔹 **می‌تونی بپرسی:**
• دانشکده من کجاست؟
• ساعت کاری کتابخانه چیه؟
• چطور ثبت‌نام کنم؟
• آدرس خوابگاه کجاست؟

🔹 **محدودیت روزانه:** {rate_limit} پیام

💡 می‌تونی پیام صوتی هم بفرستی!
💡 می‌تونی به فارسی یا انگلیسی بپرسی!""",

    "not_registered": """❌ شما هنوز ثبت‌نام نکرده‌اید!

لطفاً ابتدا با کد دانشجویی خود ثبت‌نام کنید:

👈 /login کد_دانشجویی

مثال: `/login 4020020031`""",

    "login_usage": """❌ فرمت دستور اشتباه است!

برای ثبت‌نام از این فرمت استفاده کن:

👈 /login کد_دانشجویی

مثال: `/login 4023020031`""",

    "status": """📊 **وضعیت اکانت شما**

👤 نام: {name}
🎓 کد دانشجویی: {student_code}
📨 پیام‌های امروز: {used}/{limit}
⏳ باقی‌مانده: {remaining}"""
}

MESSAGES_EN = {
    "welcome": """Hello {name}! 👋

I'm **Kharazmichi** 🤖 - Kharazmi University's AI Assistant!

Ask me anything about Kharazmi University! From faculty locations to programs and university services.

⚠️ To use, you must first register with your student ID:

👉 /login student_id

Example: `/login 4023030011`

🌍 دانشجویان ایرانی: برای فارسی /help را بزنید""",

    "help": """📚 **Kharazmichi Guide**

🔹 **Commands:**
• /start - Start conversation
• /login student_id - Register with student ID
• /help_en - Help (English)
• /help - راهنما (Persian)
• /status - Account status and remaining messages

🔹 **You can ask:**
• Where is my faculty?
• What are the library hours?
• How do I register?
• Where is the dormitory?

🔹 **Daily limit:** {rate_limit} messages

💡 You can send voice messages too!
💡 You can ask in English or Persian!""",

    "not_registered": """❌ You are not registered yet!

Please register first with your student ID:

👉 /login student_id

Example: `/login 4020020031`""",

    "login_usage": """❌ Wrong command format!

Use this format to register:

👉 /login student_id

Example: `/login 4023020031`""",

    "status": """📊 **Your Account Status**

👤 Name: {name}
🎓 Student ID: {student_code}
📨 Today's messages: {used}/{limit}
⏳ Remaining: {remaining}"""
}


class CommandHandlers:
    """Handles Telegram bot commands."""

    def __init__(
        self,
        auth_service: AuthService = None,
        rate_limiter: RateLimiter = None
    ):
        self.auth_service = auth_service or AuthService()
        self.rate_limiter = rate_limiter or RateLimiter()

    async def start_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /start command - Bilingual."""
        user = update.effective_user
        name = user.first_name or user.username or "Friend"
        
        # Default to Persian
        await update.message.reply_text(
            MESSAGES_FA["welcome"].format(name=name)
        )
        logger.info(f"User {user.id} started the bot")

    async def help_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /help command - Persian."""
        from src.config import settings
        
        await update.message.reply_text(
            MESSAGES_FA["help"].format(rate_limit=settings.rate_limit_per_day)
        )

    async def help_en_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /help_en command - English."""
        from src.config import settings
        
        await update.message.reply_text(
            MESSAGES_EN["help"].format(rate_limit=settings.rate_limit_per_day)
        )

    async def login_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /login command - Bilingual."""
        user = update.effective_user
        message_text = update.message.text
        
        # Parse student code from command
        student_code = self.auth_service.parse_login_command(message_text)
        
        if not student_code:
            # Send both languages
            await update.message.reply_text(
                MESSAGES_FA["login_usage"] + "\n\n─────\n\n" + MESSAGES_EN["login_usage"]
            )
            return
        
        # Attempt registration
        success, message = await self.auth_service.register_user(
            telegram_id=user.id,
            student_code=student_code,
            username=user.username,
            first_name=user.first_name
        )
        
        await update.message.reply_text(message)
        
        if success:
            logger.info(f"User {user.id} registered with code {student_code}")

    async def status_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /status command - Bilingual."""
        user = update.effective_user
        
        # Check if registered
        db_user = await self.auth_service.get_user(user.id)
        
        if not db_user:
            # Send both languages
            await update.message.reply_text(
                MESSAGES_FA["not_registered"] + "\n\n─────\n\n" + MESSAGES_EN["not_registered"]
            )
            return
        
        # Get rate limit status
        used, remaining = await self.rate_limiter.get_status(user.id)
        from src.config import settings
        
        name = db_user.first_name or db_user.username or "User"
        
        # Send Persian status
        await update.message.reply_text(
            MESSAGES_FA["status"].format(
                name=name,
                student_code=db_user.student_code,
                used=used,
                limit=settings.rate_limit_per_day,
                remaining=remaining
            )
        )
