from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
class TestTranscriptionPreviewAPI:
    async def _create_user_and_token(self, client):
        await client.post(
            "/auth/register",
            json={
                "username": "previewuser",
                "email": "preview@example.com",
                "password": "PreviewPass1!",
            },
        )
        login_resp = await client.post(
            "/auth/login",
            json={
                "email": "preview@example.com",
                "password": "PreviewPass1!",
            },
        )
        return login_resp.json()["access_token"]

    async def test_preview_transcription_success(self, client):
        token = await self._create_user_and_token(client)

        with patch(
            "app.services.transcription_service.transcribe_audio_content",
            new=AsyncMock(return_value="Preview transcript"),
        ) as mock_transcribe:
            resp = await client.post(
                "/transcription/preview",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": ("recorded-audio.webm", b"audio-bytes", "audio/webm;codecs=opus")},
            )

        assert resp.status_code == 200
        assert resp.json() == {"transcript": "Preview transcript"}
        mock_transcribe.assert_awaited_once()

    async def test_preview_transcription_returns_null_when_transcriber_fails_gracefully(self, client):
        token = await self._create_user_and_token(client)

        with patch(
            "app.services.transcription_service.transcribe_audio_content",
            new=AsyncMock(return_value=None),
        ):
            resp = await client.post(
                "/transcription/preview",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": ("recorded-audio.webm", b"audio-bytes", "audio/webm")},
            )

        assert resp.status_code == 200
        assert resp.json() == {"transcript": None}

    async def test_preview_transcription_rejects_invalid_file_type(self, client):
        token = await self._create_user_and_token(client)

        resp = await client.post(
            "/transcription/preview",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("photo.png", b"png-bytes", "image/png")},
        )

        assert resp.status_code == 400
        assert "Unsupported mime type" in resp.json()["detail"]

    async def test_preview_transcription_rejects_empty_file(self, client):
        token = await self._create_user_and_token(client)

        resp = await client.post(
            "/transcription/preview",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("empty.webm", b"", "audio/webm")},
        )

        assert resp.status_code == 400
        assert resp.json()["detail"] == "Uploaded file is empty"

    async def test_preview_transcription_rejects_oversized_file(self, client, monkeypatch):
        token = await self._create_user_and_token(client)
        monkeypatch.setattr("app.services.media_validation.MAX_MEDIA_UPLOAD_BYTES", 4)

        resp = await client.post(
            "/transcription/preview",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("large.webm", b"12345", "audio/webm")},
        )

        assert resp.status_code == 413
        assert resp.json()["detail"] == "File size exceeds 4 bytes"

    async def test_preview_transcription_requires_authentication(self, client):
        resp = await client.post(
            "/transcription/preview",
            files={"file": ("recorded-audio.webm", b"audio-bytes", "audio/webm")},
        )

        assert resp.status_code == 401
        assert resp.json()["detail"] == "Not authenticated"
