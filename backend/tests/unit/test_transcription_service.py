import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.db.enums import MediaType
from app.services.transcription_service import transcribe_audio_content, transcribe_media_file


class _SessionContextManager:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
class TestTranscribeAudioContent:
    async def test_returns_transcript_when_provider_succeeds(self):
        with patch(
            "app.services.transcription_service._transcribe_with_whisper",
            new=AsyncMock(return_value="Transcribed text"),
        ) as mock_stt:
            result = await transcribe_audio_content(
                filename="audio.webm",
                content=b"audio-bytes",
                mime_type="audio/webm",
            )

        assert result == "Transcribed text"
        mock_stt.assert_awaited_once()

    async def test_returns_none_when_provider_raises(self):
        with patch(
            "app.services.transcription_service._transcribe_with_whisper",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ) as mock_stt:
            result = await transcribe_audio_content(
                filename="audio.webm",
                content=b"audio-bytes",
                mime_type="audio/webm",
            )

        assert result is None
        mock_stt.assert_awaited_once()


@pytest.mark.asyncio
class TestTranscribeMediaFile:
    async def test_persists_transcript_for_audio_media(self):
        media_file_id = uuid.uuid4()
        media = SimpleNamespace(id=media_file_id, media_type=MediaType.AUDIO, transcript=None)
        db = AsyncMock()
        db.execute.return_value.scalar_one_or_none = lambda: media

        with patch(
            "app.services.transcription_service.transcribe_audio_content",
            new=AsyncMock(return_value="Audio transcript"),
        ) as mock_transcribe:
            with patch(
                "app.services.transcription_service.AsyncSessionLocal",
                return_value=_SessionContextManager(db),
            ) as mock_session_factory:
                await transcribe_media_file(
                    media_file_id=media_file_id,
                    filename="audio.webm",
                    content=b"audio-bytes",
                    mime_type="audio/webm",
                )

        assert media.transcript == "Audio transcript"
        mock_transcribe.assert_awaited_once()
        mock_session_factory.assert_called_once()
        db.commit.assert_awaited_once()

    async def test_skips_persist_when_no_transcript_is_returned(self):
        with patch(
            "app.services.transcription_service.transcribe_audio_content",
            new=AsyncMock(return_value=None),
        ) as mock_transcribe:
            with patch("app.services.transcription_service.AsyncSessionLocal") as mock_session_factory:
                await transcribe_media_file(
                    media_file_id=uuid.uuid4(),
                    filename="audio.webm",
                    content=b"audio-bytes",
                    mime_type="audio/webm",
                )

        mock_transcribe.assert_awaited_once()
        mock_session_factory.assert_not_called()

    async def test_skips_persist_for_non_audio_media(self):
        media_file_id = uuid.uuid4()
        media = SimpleNamespace(id=media_file_id, media_type=MediaType.VIDEO, transcript=None)
        db = AsyncMock()
        db.execute.return_value.scalar_one_or_none = lambda: media

        with patch(
            "app.services.transcription_service.transcribe_audio_content",
            new=AsyncMock(return_value="Should not be stored"),
        ):
            with patch(
                "app.services.transcription_service.AsyncSessionLocal",
                return_value=_SessionContextManager(db),
            ):
                await transcribe_media_file(
                    media_file_id=media_file_id,
                    filename="audio.webm",
                    content=b"audio-bytes",
                    mime_type="audio/webm",
                )

        assert media.transcript is None
        db.commit.assert_not_awaited()
