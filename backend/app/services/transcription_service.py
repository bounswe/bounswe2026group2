import asyncio
import logging
import os
import threading
import uuid
from tempfile import NamedTemporaryFile

from fastapi import UploadFile, status
from sqlalchemy import select

from app.core.config import settings
from app.db.enums import MediaType
from app.db.media_file import MediaFile
from app.db.session import AsyncSessionLocal
from app.services.ai_tagging_system import is_ai_tagging_configured, run_ai_tagging_for_story
from app.services.media_validation import read_uploaded_file_content, validate_media_upload

logger = logging.getLogger(__name__)

# Semaphore ensures at most one WhisperModel is instantiated at a time.
# Without this, concurrent requests each load their own model, multiplying peak memory.
_transcription_semaphore = threading.Semaphore(1)


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
        return await _transcribe_with_whisper(
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


async def _transcribe_with_whisper(
    *,
    filename: str,
    content: bytes,
    mime_type: str | None,
) -> str | None:
    # Model inference is synchronous and CPU-heavy, so run it off the event loop.
    return await asyncio.to_thread(
        _transcribe_with_whisper_sync,
        filename=filename,
        content=content,
        mime_type=mime_type,
    )


def _transcribe_with_whisper_sync(
    *,
    filename: str,
    content: bytes,
    mime_type: str | None,
) -> str | None:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("faster-whisper is not installed") from exc

    suffix = os.path.splitext(filename)[1] or ".audio"
    with NamedTemporaryFile(suffix=suffix, delete=True) as temp_audio:
        temp_audio.write(content)
        temp_audio.flush()

        with _transcription_semaphore:
            model = WhisperModel(
                settings.TRANSCRIPTION_MODEL,
                device=settings.TRANSCRIPTION_DEVICE,
                compute_type=settings.TRANSCRIPTION_COMPUTE_TYPE,
            )
            try:
                segments, _info = model.transcribe(temp_audio.name, beam_size=5)
                transcript = " ".join(
                    segment.text.strip() for segment in segments if getattr(segment, "text", "").strip()
                )
            finally:
                del model

    if not transcript:
        logger.warning("Whisper transcription for %s returned no text", filename)
        return None

    return transcript
