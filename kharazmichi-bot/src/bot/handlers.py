"""
Telegram message handlers for text and voice messages.
"""

from telegram import Update
from telegram.ext import ContextTypes

from loguru import logger

from src.config import settings
from src.services.auth import AuthService
from src.services.rate_limiter import RateLimiter
from src.services.ai_agent import get_ai_agent
from src.services.voice import VoiceService


class MessageHandlers:
    """Handles incoming text and voice messages."""

    def __init__(
        self,
        auth_service: AuthService = None,
        rate_limiter: RateLimiter = None,
        voice_service: VoiceService = None
    ):
        self.auth_service = auth_service or AuthService()
        self.rate_limiter = rate_limiter or RateLimiter()
        self.voice_service = voice_service or VoiceService()
        self._ai_agent = None  # Lazy loaded
    
    async def _get_agent(self):
        """Lazy load AI agent"""
        if self._ai_agent is None:
            self._ai_agent = await get_ai_agent()
        return self._ai_agent

    async def handle_text_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle incoming text messages."""
        user = update.effective_user
        message_text = update.message.text
        
        logger.info(f"Text message from {user.id}: {message_text[:50]}...")
        
        # Process the message
        await self._process_message(update, context, message_text)

    async def handle_voice_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle incoming voice messages."""
        user = update.effective_user
        voice = update.message.voice
        
        logger.info(f"Voice message from {user.id}, duration: {voice.duration}s")
        
        # Check authentication first
        if not await self.auth_service.is_authenticated(user.id):
            await update.message.reply_text(
                "❌ شما هنوز ثبت‌نام نکرده‌اید!\n\nلطفاً ابتدا با /login کد_دانشجویی ثبت‌نام کنید.\n\n─────\n\n❌ You are not registered yet!\n\nPlease register first with /login student_id"
            )
            return
        
        # Check rate limit
        is_allowed, limit_msg, _ = await self.rate_limiter.check_and_log(
            telegram_id=user.id,
            message_text="[voice message]"
        )
        
        if not is_allowed:
            await update.message.reply_text(limit_msg)
            return
        
        # Send processing indicator
        processing_msg = await update.message.reply_text("🎤 در حال پردازش پیام صوتی...")
        
        try:
            # Get file from Telegram
            file = await context.bot.get_file(voice.file_id)
            
            # Transcribe voice
            transcribed_text = await self.voice_service.transcribe_telegram_voice(
                file_path=file.file_path,
                bot_token=settings.telegram_bot_token
            )
            
            if not transcribed_text:
                await processing_msg.edit_text(
                    "❌ متأسفانه نتونستم پیام صوتی رو پردازش کنم. لطفاً دوباره امتحان کن یا پیام متنی بفرست."
                )
                return
            
            # Delete processing message
            await processing_msg.delete()
            
            # Show what was transcribed
            await update.message.reply_text(f"🎤 شنیدم: {transcribed_text}")
            
            # Generate AI response
            agent = await self._get_agent()
            response, location = await agent.chat(user_message=transcribed_text)
            
            # Send response
            await update.message.reply_text(response)
            
            # Send location if found in knowledge base
            if location:
                await context.bot.send_location(
                    chat_id=update.effective_chat.id,
                    latitude=location["latitude"],
                    longitude=location["longitude"]
                )
                logger.info(f"Sent location to user {user.id}: {location}")
            
        except Exception as e:
            logger.error(f"Error processing voice message: {e}")
            await processing_msg.edit_text(
                "❌ خطایی در پردازش پیام صوتی رخ داد. لطفاً دوباره تلاش کنید."
            )

    async def _process_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        message_text: str
    ) -> None:
        """Process a message (text or transcribed voice)."""
        user = update.effective_user
        
        # Check authentication
        if not await self.auth_service.is_authenticated(user.id):
            await update.message.reply_text(
                "❌ شما هنوز ثبت‌نام نکرده‌اید!\n\nلطفاً ابتدا با /login کد_دانشجویی ثبت‌نام کنید.\n\n─────\n\n❌ You are not registered yet!\n\nPlease register first with /login student_id"
            )
            return
        
        # Check rate limit
        is_allowed, limit_msg, remaining = await self.rate_limiter.check_and_log(
            telegram_id=user.id,
            message_text=message_text
        )
        
        if not is_allowed:
            await update.message.reply_text(limit_msg)
            return
        
        # Send typing indicator
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )
        
        try:
            # AI Agent handles everything - decides what to search, when to send location
            agent = await self._get_agent()
            response, location = await agent.chat(user_message=message_text)
            
            # Add remaining messages info if running low
            if remaining <= 5 and remaining > 0:
                response += f"\n\n⚠️ {remaining} پیام از سهمیه روزانه باقی مونده"
            
            # Send text response
            await update.message.reply_text(response)
            
            # Send location if AI decided to (via tool call)
            if location:
                await context.bot.send_location(
                    chat_id=update.effective_chat.id,
                    latitude=location["latitude"],
                    longitude=location["longitude"]
                )
                logger.info(f"Sent location to user {user.id}: {location}")
            
        except Exception as e:
            logger.error(f"Error processing message from {user.id}: {e}")
            await update.message.reply_text(
                "❌ یه مشکلی پیش اومد، دوباره امتحان کن."
            )


class ErrorHandler:
    """Handles errors in the bot."""

    @staticmethod
    async def handle_error(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Log errors and notify user."""
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ متأسفانه خطایی رخ داد. لطفاً دوباره تلاش کنید."
            )
