"""
Main application entry point.
FastAPI server with Telegram bot integration.
"""

import asyncio
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from loguru import logger
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

from src.config import settings
from src.bot.commands import CommandHandlers
from src.bot.handlers import MessageHandlers, ErrorHandler


# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=settings.log_level,
    colorize=True
)
logger.add(
    "logs/bot.log",
    rotation="10 MB",
    retention="7 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG"
)


# Global bot application instance
bot_app: Application = None


def create_bot_application() -> Application:
    """Create and configure the Telegram bot application."""
    # Initialize handlers
    command_handlers = CommandHandlers()
    message_handlers = MessageHandlers()
    
    # Create application
    application = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .build()
    )
    
    # Register command handlers (Bilingual support)
    application.add_handler(CommandHandler("start", command_handlers.start_command))
    application.add_handler(CommandHandler("help", command_handlers.help_command))
    application.add_handler(CommandHandler("help_en", command_handlers.help_en_command))
    application.add_handler(CommandHandler("login", command_handlers.login_command))
    application.add_handler(CommandHandler("status", command_handlers.status_command))
    
    # Register message handlers
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            message_handlers.handle_text_message
        )
    )
    application.add_handler(
        MessageHandler(
            filters.VOICE,
            message_handlers.handle_voice_message
        )
    )
    
    # Register error handler
    application.add_error_handler(ErrorHandler.handle_error)
    
    logger.info("Bot application created successfully")
    return application


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global bot_app
    
    logger.info("Starting Kharazmichi Bot...")
    logger.info(f"Bot name: {settings.bot_name}")
    logger.info(f"Rate limit: {settings.rate_limit_per_day} messages/day")
    logger.info(f"Memory size: {settings.conversation_memory_size} messages")
    
    # Create bot application
    bot_app = create_bot_application()
    
    if settings.is_webhook_mode:
        # Webhook mode - set webhook URL
        logger.info(f"Running in WEBHOOK mode: {settings.telegram_webhook_url}")
        await bot_app.initialize()
        await bot_app.bot.set_webhook(
            url=f"{settings.telegram_webhook_url}/webhook",
            allowed_updates=["message"]
        )
        await bot_app.start()
    else:
        # Polling mode - for local development
        logger.info("Running in POLLING mode")
        await bot_app.initialize()
        await bot_app.start()
        await bot_app.updater.start_polling(allowed_updates=["message"])
    
    logger.info("Bot started successfully! ✅")
    
    yield
    
    # Shutdown
    logger.info("Shutting down bot...")
    if settings.is_webhook_mode:
        await bot_app.bot.delete_webhook()
    else:
        await bot_app.updater.stop()
    await bot_app.stop()
    await bot_app.shutdown()
    logger.info("Bot shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Kharazmichi Bot API",
    description="Telegram bot for Kharazmi University students",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "running",
        "bot": settings.bot_name,
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "bot_name": settings.bot_name,
        "mode": "webhook" if settings.is_webhook_mode else "polling",
        "rate_limit": settings.rate_limit_per_day
    }


@app.post("/webhook")
async def webhook(request: Request) -> Response:
    """Handle incoming Telegram webhook updates."""
    if not bot_app:
        logger.error("Bot application not initialized")
        return Response(status_code=500)
    
    try:
        data = await request.json()
        update = Update.de_json(data, bot_app.bot)
        await bot_app.process_update(update)
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return Response(status_code=500)


def main():
    """Run the application."""
    import uvicorn
    
    logger.info(f"Starting server on {settings.host}:{settings.port}")
    
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()
