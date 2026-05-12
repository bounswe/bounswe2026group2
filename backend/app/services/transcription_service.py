import logging
import uuid

import httpx
from fastapi import UploadFile, status
from sqlalchemy import select

from app.core.config import settings
from app.db.enums import MediaType
from app.db.media_file import MediaFile
from app.db.session import AsyncSessionLocal
from app.services.ai_tagging_system import is_ai_tagging_configured, run_ai_tagging_for_story
from app.services.media_validation import read_uploaded_file_content, validate_media_upload

logger = logging.getLogger(__name__)

_OPENAI_TRANSCRIPTION_URL = "https://api.openai.com/v1/audio/transcriptions"


async def transcribe_media_file(
    *,
    media_file_id: uuid.UUID,
    filename: str,
    content: bytes,
    mime_type: str | None,
) -> None:
    transcript = await transcribe_audio_content(
        filename=filename,
        content=content,
        mime_type=mime_type,
    )
    if not transcript:
        return

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(MediaFile).where(MediaFile.id == media_file_id))
            media = result.scalar_one_or_none()
            if media is None:
                logger.warning("Skipping transcript persistence because media file %s was not found", media_file_id)
                return

            if media.media_type != MediaType.AUDIO:
                logger.warning("Skipping transcript persistence because media file %s is not audio", media_file_id)
                return

            media.transcript = transcript
            await db.commit()

            if is_ai_tagging_configured():
                await run_ai_tagging_for_story(media.story_id)
    except Exception:
        logger.exception("Failed to persist transcript for media file %s", media_file_id)


async def transcribe_audio_content(
    *,
    filename: str,
    content: bytes,
    mime_type: str | None,
) -> str | None:
    try:
        return await _transcribe_with_openai(
            filename=filename,
            content=content,
            mime_type=mime_type,
        )
    except Exception:
        logger.exception("Audio transcription failed for %s", filename)
        return None


async def preview_audio_transcription(file: UploadFile) -> str | None:
    normalized_content_type = validate_media_upload(
        file,
        MediaType.AUDIO,
        invalid_mime_status=status.HTTP_400_BAD_REQUEST,
    )
    file_bytes = await read_uploaded_file_content(file)
    return await transcribe_audio_content(
        filename=file.filename,
        content=file_bytes,
        mime_type=normalized_content_type,
    )


async def _transcribe_with_openai(
    *,
    filename: str,
    content: bytes,
    mime_type: str | None,
) -> str | None:
    if not settings.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY is not set; skipping transcription")
        return None

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            _OPENAI_TRANSCRIPTION_URL,
            headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
            data={"model": settings.AI_WHISPER_MODEL},
            files={"file": (filename, content, mime_type or "application/octet-stream")},
        )
        response.raise_for_status()

    transcript = response.json().get("text", "").strip()
    if not transcript:
        logger.warning("OpenAI Whisper returned no text for %s", filename)
        return None

    return transcript
