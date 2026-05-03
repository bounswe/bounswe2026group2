"""Integration tests: end-to-end story flow with recorded audio/video media.

Covers issue #211 acceptance criteria:
- Recorded audio/webm and video/webm are accepted by the media upload API.
- Uploaded recorded media is linked to the correct story.
- Story detail returns recorded media files in sort_order with correct metadata.
- Codec parameter strings (e.g. audio/webm;codecs=opus) are accepted.
- Mixed-case MIME types (e.g. Audio/WebM;Codecs=Opus) are accepted.
"""

import pytest


@pytest.mark.asyncio
class TestRecordedMediaUploadFlow:
    async def _register_and_login(self, client, username, email, password):
        await client.post(
            "/auth/register",
            json={"username": username, "email": email, "password": password},
        )
        login_resp = await client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
        return login_resp.json()["access_token"]

    async def _create_story(self, client, token, title="Recorded Story"):
        resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": title,
                "content": "A story capturing local history with live media.",
                "summary": "Recorded on location.",
                "place_name": "Galata Tower",
                "latitude": 41.0256,
                "longitude": 28.9742,
                "date_start": 2024,
                "date_end": 2024,
            },
        )
        assert resp.status_code == 201
        return resp.json()["id"]

    async def test_upload_recorded_audio_webm_is_accepted(self, client, monkeypatch):
        monkeypatch.setattr("app.services.story_service.upload_bytes", lambda **kwargs: None)
        token = await self._register_and_login(client, "recaudio1", "recaudio1@example.com", "RecAudio1!")
        story_id = await self._create_story(client, token)

        resp = await client.post(
            f"/stories/{story_id}/media",
            headers={"Authorization": f"Bearer {token}"},
            data={"media_type": "audio", "sort_order": "0"},
            files={"file": ("recorded-audio-2024-06-01T12-00-00.webm", b"audio-webm-bytes", "audio/webm")},
        )

        assert resp.status_code == 201
        media = resp.json()["media"]
        assert media["story_id"] == story_id
        assert media["media_type"] == "audio"
        assert media["mime_type"] == "audio/webm"
        assert media["original_filename"] == "recorded-audio-2024-06-01T12-00-00.webm"
        assert media["sort_order"] == 0
        assert "media_url" in media

    async def test_upload_recorded_audio_webm_with_codec_param_is_accepted(self, client, monkeypatch):
        monkeypatch.setattr("app.services.story_service.upload_bytes", lambda **kwargs: None)
        token = await self._register_and_login(client, "recaudio2", "recaudio2@example.com", "RecAudio2!")
        story_id = await self._create_story(client, token)

        resp = await client.post(
            f"/stories/{story_id}/media",
            headers={"Authorization": f"Bearer {token}"},
            data={"media_type": "audio", "sort_order": "0"},
            files={"file": ("clip.webm", b"opus-bytes", "audio/webm;codecs=opus")},
        )

        assert resp.status_code == 201
        media = resp.json()["media"]
        assert media["media_type"] == "audio"
        assert media["mime_type"] == "audio/webm;codecs=opus"

    async def test_upload_recorded_audio_webm_mixed_case_mime_is_accepted(self, client, monkeypatch):
        monkeypatch.setattr("app.services.story_service.upload_bytes", lambda **kwargs: None)
        token = await self._register_and_login(client, "recaudio3", "recaudio3@example.com", "RecAudio3!")
        story_id = await self._create_story(client, token)

        resp = await client.post(
            f"/stories/{story_id}/media",
            headers={"Authorization": f"Bearer {token}"},
            data={"media_type": "audio", "sort_order": "0"},
            files={"file": ("clip.webm", b"opus-bytes", "Audio/WebM;Codecs=Opus")},
        )

        assert resp.status_code == 201
        assert resp.json()["media"]["media_type"] == "audio"

    async def test_upload_recorded_video_webm_is_accepted(self, client, monkeypatch):
        monkeypatch.setattr("app.services.story_service.upload_bytes", lambda **kwargs: None)
        token = await self._register_and_login(client, "recvideo1", "recvideo1@example.com", "RecVideo1!")
        story_id = await self._create_story(client, token)

        resp = await client.post(
            f"/stories/{story_id}/media",
            headers={"Authorization": f"Bearer {token}"},
            data={"media_type": "video", "sort_order": "0"},
            files={"file": ("recorded-video-2024-06-01T12-00-00.webm", b"video-webm-bytes", "video/webm")},
        )

        assert resp.status_code == 201
        media = resp.json()["media"]
        assert media["story_id"] == story_id
        assert media["media_type"] == "video"
        assert media["mime_type"] == "video/webm"
        assert media["original_filename"] == "recorded-video-2024-06-01T12-00-00.webm"
        assert media["sort_order"] == 0
        assert "media_url" in media

    async def test_upload_recorded_video_webm_with_codec_param_is_accepted(self, client, monkeypatch):
        monkeypatch.setattr("app.services.story_service.upload_bytes", lambda **kwargs: None)
        token = await self._register_and_login(client, "recvideo2", "recvideo2@example.com", "RecVideo2!")
        story_id = await self._create_story(client, token)

        resp = await client.post(
            f"/stories/{story_id}/media",
            headers={"Authorization": f"Bearer {token}"},
            data={"media_type": "video", "sort_order": "0"},
            files={"file": ("clip.webm", b"vp8-bytes", "video/webm;codecs=vp8,opus")},
        )

        assert resp.status_code == 201
        media = resp.json()["media"]
        assert media["media_type"] == "video"
        assert media["mime_type"] == "video/webm;codecs=vp8,opus"


@pytest.mark.asyncio
class TestRecordedMediaStoryDetailFlow:
    """End-to-end: create story → attach recorded audio + video → verify story detail."""

    async def _register_and_login(self, client, username, email, password):
        await client.post(
            "/auth/register",
            json={"username": username, "email": email, "password": password},
        )
        login_resp = await client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
        return login_resp.json()["access_token"]

    async def test_story_detail_includes_recorded_audio_and_video(self, client, monkeypatch):
        monkeypatch.setattr("app.services.story_service.upload_bytes", lambda **kwargs: None)
        token = await self._register_and_login(client, "recboth1", "recboth1@example.com", "RecBoth1!")

        create_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Field Recording Story",
                "content": "Captured on location with audio and video.",
                "summary": "Live recording at historical site.",
                "place_name": "Hagia Sophia",
                "latitude": 41.0086,
                "longitude": 28.9802,
                "date_start": 2024,
                "date_end": 2024,
            },
        )
        assert create_resp.status_code == 201
        story_id = create_resp.json()["id"]

        audio_resp = await client.post(
            f"/stories/{story_id}/media",
            headers={"Authorization": f"Bearer {token}"},
            data={"media_type": "audio", "sort_order": "0"},
            files={"file": ("recorded-audio.webm", b"audio-bytes", "audio/webm;codecs=opus")},
        )
        assert audio_resp.status_code == 201

        video_resp = await client.post(
            f"/stories/{story_id}/media",
            headers={"Authorization": f"Bearer {token}"},
            data={"media_type": "video", "sort_order": "1"},
            files={"file": ("recorded-video.webm", b"video-bytes", "video/webm")},
        )
        assert video_resp.status_code == 201

        detail_resp = await client.get(f"/stories/{story_id}")
        assert detail_resp.status_code == 200
        data = detail_resp.json()

        assert len(data["media_files"]) == 2
        media_files = data["media_files"]

        assert media_files[0]["media_type"] == "audio"
        assert media_files[0]["mime_type"] == "audio/webm;codecs=opus"
        assert media_files[0]["original_filename"] == "recorded-audio.webm"
        assert media_files[0]["sort_order"] == 0

        assert media_files[1]["media_type"] == "video"
        assert media_files[1]["mime_type"] == "video/webm"
        assert media_files[1]["original_filename"] == "recorded-video.webm"
        assert media_files[1]["sort_order"] == 1

    async def test_story_detail_recorded_media_urls_are_present(self, client, monkeypatch):
        monkeypatch.setattr("app.services.story_service.upload_bytes", lambda **kwargs: None)
        token = await self._register_and_login(client, "recboth2", "recboth2@example.com", "RecBoth2!")

        create_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Media URL Story",
                "content": "Verifying media_url fields.",
                "summary": "URL check.",
                "place_name": "Topkapi Palace",
                "latitude": 41.0115,
                "longitude": 28.9833,
                "date_start": 2024,
                "date_end": 2024,
            },
        )
        assert create_resp.status_code == 201
        story_id = create_resp.json()["id"]

        await client.post(
            f"/stories/{story_id}/media",
            headers={"Authorization": f"Bearer {token}"},
            data={"media_type": "audio", "sort_order": "0"},
            files={"file": ("audio.webm", b"bytes", "audio/webm")},
        )

        detail_resp = await client.get(f"/stories/{story_id}")
        assert detail_resp.status_code == 200
        media_files = detail_resp.json()["media_files"]

        assert len(media_files) == 1
        media = media_files[0]
        assert media["media_url"] is not None
        assert media["media_url"] != ""
        assert "audio" in media["media_url"]

    async def test_recorded_media_linked_to_correct_story_only(self, client, monkeypatch):
        monkeypatch.setattr("app.services.story_service.upload_bytes", lambda **kwargs: None)
        token = await self._register_and_login(client, "recboth3", "recboth3@example.com", "RecBoth3!")

        story_a_id = (
            await client.post(
                "/stories",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "title": "Story A",
                    "content": "Content A",
                    "summary": "Summary A",
                    "place_name": "Istanbul",
                    "latitude": 41.0082,
                    "longitude": 28.9784,
                    "date_start": 2024,
                    "date_end": 2024,
                },
            )
        ).json()["id"]

        story_b_id = (
            await client.post(
                "/stories",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "title": "Story B",
                    "content": "Content B",
                    "summary": "Summary B",
                    "place_name": "Ankara",
                    "latitude": 39.9334,
                    "longitude": 32.8597,
                    "date_start": 2024,
                    "date_end": 2024,
                },
            )
        ).json()["id"]

        await client.post(
            f"/stories/{story_a_id}/media",
            headers={"Authorization": f"Bearer {token}"},
            data={"media_type": "audio", "sort_order": "0"},
            files={"file": ("for-a.webm", b"bytes", "audio/webm")},
        )

        detail_a = await client.get(f"/stories/{story_a_id}")
        detail_b = await client.get(f"/stories/{story_b_id}")

        assert len(detail_a.json()["media_files"]) == 1
        assert detail_a.json()["media_files"][0]["original_filename"] == "for-a.webm"
        assert len(detail_b.json()["media_files"]) == 0
