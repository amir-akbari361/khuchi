"""
Voice transcription service using OpenAI Whisper.
"""

import tempfile
from pathlib import Path
from typing import Optional

import httpx
from loguru import logger
from openai import OpenAI

from src.config import settings


class VoiceService:
    """Service for voice message transcription."""

    def __init__(self, openai_client: Optional[OpenAI] = None):
        self.openai_client = openai_client or OpenAI(api_key=settings.openai_api_key)
        self.model = "whisper-1"

    async def transcribe_telegram_voice(
        self,
        file_path: str,
        bot_token: str
    ) -> Optional[str]:
        """
        Download and transcribe a Telegram voice message.
        
        Args:
            file_path: Telegram file path (from getFile API)
            bot_token: Telegram bot token
            
        Returns:
            Transcribed text or None if failed
        """
        try:
            # Download voice file from Telegram
            download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(download_url)
                response.raise_for_status()
                voice_data = response.content

            # Save to temp file and transcribe
            return await self._transcribe_audio_data(voice_data, "ogg")

        except Exception as e:
            logger.error(f"Error transcribing Telegram voice: {e}")
            return None

    async def _transcribe_audio_data(
        self,
        audio_data: bytes,
        file_extension: str = "ogg"
    ) -> Optional[str]:
        """
        Transcribe audio data using Whisper.
        
        Args:
            audio_data: Raw audio bytes
            file_extension: Audio file extension
            
        Returns:
            Transcribed text
        """
        try:
            # Create temp file
            with tempfile.NamedTemporaryFile(
                suffix=f".{file_extension}",
                delete=False
            ) as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name

            try:
                # Transcribe with Whisper
                with open(temp_path, "rb") as audio_file:
                    response = self.openai_client.audio.transcriptions.create(
                        model=self.model,
                        file=audio_file,
                        language="fa"  # Persian
                    )

                transcribed_text = response.text.strip()
                logger.debug(f"Transcribed voice: {transcribed_text[:100]}...")
                return transcribed_text

            finally:
                # Clean up temp file
                Path(temp_path).unlink(missing_ok=True)

        except Exception as e:
            logger.error(f"Error in Whisper transcription: {e}")
            return None
