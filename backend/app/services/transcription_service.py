import asyncio
import functools
import logging
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from tempfile import NamedTemporaryFile

from fastapi import UploadFile, status
from google import genai
from google.genai import types
from sqlalchemy import select

from app.core.config import settings
from app.db.enums import MediaType
from app.db.media_file import MediaFile
from app.db.session import AsyncSessionLocal
from app.services.ai_tagging_system import is_ai_tagging_configured, run_ai_tagging_for_story
from app.services.media_validation import read_uploaded_file_content, validate_media_upload

logger = logging.getLogger(__name__)

# Single-worker executor: all transcription work is serialised before a thread is
# allocated, so no threadpool slots are wasted waiting and only one WhisperModel
# is ever active. Both preview and background calls share this queue.
_TRANSCRIPTION_EXECUTOR = ThreadPoolExecutor(max_workers=1)
_GEMINI_TRANSCRIPTION_PROMPT = (
    "Generate an accurate transcript of the speech in this audio file. "
    "Return only the transcript text. Do not summarize, translate, add timestamps, "
    "or include explanations. If no speech is present, return an empty response."
)
_GEMINI_MIME_TYPE_ALIASES = {
    "audio/mpeg": "audio/mp3",
}


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
        return await _transcribe_with_configured_provider(
            filename=filename,
            content=content,
            mime_type=mime_type,
        )
    except Exception:
        logger.exception("Audio transcription failed for %s", filename)
        return None


async def _transcribe_with_configured_provider(
    *,
    filename: str,
    content: bytes,
    mime_type: str | None,
) -> str | None:
    if settings.STT_PROVIDER.lower() != "gemini":
        return await _transcribe_with_whisper(
            filename=filename,
            content=content,
            mime_type=mime_type,
        )

    try:
        transcript = await _transcribe_with_gemini(
            filename=filename,
            content=content,
            mime_type=mime_type,
        )
        if transcript:
            return transcript
        logger.warning("Gemini transcription for %s returned no text; falling back to local Whisper", filename)
    except Exception:
        logger.exception("Gemini transcription failed for %s; falling back to local Whisper", filename)

    return await _transcribe_with_whisper(
        filename=filename,
        content=content,
        mime_type=mime_type,
    )


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
    loop = asyncio.get_running_loop()
    fn = functools.partial(_transcribe_with_whisper_sync, filename=filename, content=content, mime_type=mime_type)
    return await loop.run_in_executor(_TRANSCRIPTION_EXECUTOR, fn)


async def _transcribe_with_gemini(
    *,
    filename: str,
    content: bytes,
    mime_type: str | None,
) -> str | None:
    return await asyncio.to_thread(
        _transcribe_with_gemini_sync,
        filename=filename,
        content=content,
        mime_type=mime_type,
    )


def _transcribe_with_gemini_sync(
    *,
    filename: str,
    content: bytes,
    mime_type: str | None,
) -> str | None:
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured")

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    try:
        response = client.models.generate_content(
            model=settings.STT_MODEL,
            contents=[
                _GEMINI_TRANSCRIPTION_PROMPT,
                types.Part.from_bytes(
                    data=content,
                    mime_type=_normalize_gemini_mime_type(mime_type),
                ),
            ],
        )
    finally:
        client.close()

    transcript = getattr(response, "text", None)
    if not isinstance(transcript, str):
        raise ValueError("Could not extract Gemini transcription text")

    transcript = transcript.strip()
    if not transcript:
        logger.warning("Gemini transcription for %s returned no text", filename)
        return None

    return transcript


def _normalize_gemini_mime_type(mime_type: str | None) -> str:
    if not mime_type:
        return "audio/mp3"
    return _GEMINI_MIME_TYPE_ALIASES.get(mime_type, mime_type)


@lru_cache(maxsize=1)
def _load_whisper_model():
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("faster-whisper is not installed") from exc

    return WhisperModel(
        settings.TRANSCRIPTION_MODEL,
        device=settings.TRANSCRIPTION_DEVICE,
        compute_type=settings.TRANSCRIPTION_COMPUTE_TYPE,
    )


def _transcribe_with_whisper_sync(
    *,
    filename: str,
    content: bytes,
    mime_type: str | None,
) -> str | None:
    suffix = os.path.splitext(filename)[1] or ".audio"
    with NamedTemporaryFile(suffix=suffix, delete=True) as temp_audio:
        temp_audio.write(content)
        temp_audio.flush()

        model = _load_whisper_model()
        segments, _info = model.transcribe(temp_audio.name, beam_size=5)
        transcript = " ".join(segment.text.strip() for segment in segments if getattr(segment, "text", "").strip())

    if not transcript:
        logger.warning("Whisper transcription for %s returned no text", filename)
        return None

    return transcript
