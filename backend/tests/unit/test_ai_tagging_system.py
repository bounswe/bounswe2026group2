import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai_tagging_system import (
    build_ai_tagging_prompt,
    build_ai_tagging_request_payload,
    generate_ai_story_tags,
    parse_ai_generated_tags,
    run_ai_tagging_for_story,
    trigger_ai_tagging_if_ready,
)


class TestStoryTaggingPrompt:
    def test_prompt_prioritizes_location_date_and_content(self):
        prompt = build_ai_tagging_prompt(
            title="A Day in Bogazici",
            content="A personal story about sports memories near the Bosphorus.",
            place_name="Istanbul",
            date_label="1998",
        )

        assert "location-based story-sharing application" in prompt
        assert "Return 5 to 10 short, useful tags in English." in prompt
        assert "Location: Istanbul" in prompt
        assert "Date: 1998" in prompt
        assert "A personal story about sports memories" in prompt

    def test_request_payload_wraps_prompt_in_chat_shape(self):
        payload = build_ai_tagging_request_payload(
            title="Title",
            content="Content",
            place_name="Ankara",
            date_label="1923",
        )

        assert payload["model"]
        assert "Title" in payload["contents"]
        assert "Ankara" in payload["contents"]


class TestGeneratedTagParsing:
    def test_parse_ai_generated_tags_from_json_object(self):
        tags = parse_ai_generated_tags('{"tags": ["  Bogazici ", "Turkiye", "bogazici"]}')

        assert tags == ["bogazici", "turkiye"]

    def test_parse_ai_generated_tags_from_openai_style_payload(self):
        tags = parse_ai_generated_tags(
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"tags": ["spor", "istanbul", "tarih"]}',
                        }
                    }
                ]
            }
        )

        assert tags == ["spor", "istanbul", "tarih"]

    def test_parse_ai_generated_tags_from_response_text_attribute(self):
        tags = parse_ai_generated_tags(SimpleNamespace(text='{"tags": ["spor", "istanbul"]}'))

        assert tags == ["spor", "istanbul"]

    def test_parse_ai_generated_tags_falls_back_to_comma_separated_text(self):
        tags = parse_ai_generated_tags("Bogazici, Turkey, Sports")

        assert tags == ["bogazici", "turkey", "sports"]

    def test_parse_ai_generated_tags_strips_markdown_code_fence(self):
        raw = '```json\n{"tags": ["istanbul", "architecture", "ottoman"]}\n```'
        tags = parse_ai_generated_tags(raw)

        assert tags == ["istanbul", "architecture", "ottoman"]


class TestAiTaggingReadiness:
    def test_trigger_ai_tagging_if_ready_returns_true_for_text_only_story(self):
        story = SimpleNamespace(
            content="Ready text content",
            media_files=[],
        )

        assert trigger_ai_tagging_if_ready(story) is True

    def test_trigger_ai_tagging_if_ready_returns_false_for_audio_story_without_transcript(self):
        story = SimpleNamespace(
            content="Story content",
            media_files=[SimpleNamespace(media_type="audio", transcript=None)],
        )

        assert trigger_ai_tagging_if_ready(story) is False

    def test_trigger_ai_tagging_if_ready_returns_true_for_audio_story_with_transcript(self):
        story = SimpleNamespace(
            content="Story content",
            media_files=[SimpleNamespace(media_type="audio", transcript="Recorded transcript")],
        )

        assert trigger_ai_tagging_if_ready(story) is True

    def test_trigger_ai_tagging_if_ready_returns_false_for_blank_story_content(self):
        story = SimpleNamespace(
            content="   ",
            media_files=[],
        )

        assert trigger_ai_tagging_if_ready(story) is False


@pytest.mark.asyncio
class TestGenerateStoryTagsWithAi:
    async def test_generate_ai_story_tags_uses_gemini_client_and_parses_response(self, monkeypatch):
        monkeypatch.setattr("app.services.ai_tagging_system.settings.GEMINI_API_KEY", "secret")
        monkeypatch.setattr("app.services.ai_tagging_system.settings.AI_TAGGING_MODEL", "fake-model")

        client = MagicMock()
        client.models.generate_content.return_value = SimpleNamespace(text='{"tags": ["Bogazici", "Turkiye", "Spor"]}')

        with patch("app.services.ai_tagging_system.genai.Client", return_value=client) as client_cls:
            tags = await generate_ai_story_tags(
                title="A Day in Bogazici",
                content="A sports memory from Istanbul.",
                place_name="Istanbul",
                date_label="1998",
            )

        assert tags == ["bogazici", "turkiye", "spor"]
        client_cls.assert_called_once_with(api_key="secret")
        client.models.generate_content.assert_called_once()
        client.close.assert_called_once()

    async def test_generate_ai_story_tags_requires_gemini_configuration(self, monkeypatch):
        monkeypatch.setattr("app.services.ai_tagging_system.settings.GEMINI_API_KEY", "")

        with pytest.raises(ValueError) as exc_info:
            await generate_ai_story_tags(title="Title", content="Content")

        assert "GEMINI_API_KEY" in str(exc_info.value)


@pytest.mark.asyncio
class TestRunAiTaggingForStory:
    async def test_run_ai_tagging_for_story_returns_false_when_story_not_ready(self, monkeypatch):
        story = SimpleNamespace(
            id=uuid.uuid4(),
            title="Audio Story",
            content="Story content",
            place_name="Istanbul",
            date_start=None,
            date_end=None,
            media_files=[SimpleNamespace(media_type="audio", transcript=None)],
        )

        session = AsyncMock()
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        monkeypatch.setattr("app.services.ai_tagging_system.is_ai_tagging_configured", lambda: True)
        monkeypatch.setattr("app.services.ai_tagging_system.AsyncSessionLocal", lambda: session)
        monkeypatch.setattr("app.services.ai_tagging_system._get_story_for_ai_tagging", AsyncMock(return_value=story))
        generate_mock = AsyncMock()
        monkeypatch.setattr("app.services.ai_tagging_system.generate_ai_story_tags", generate_mock)

        result = await run_ai_tagging_for_story(story.id)

        assert result is False
        generate_mock.assert_not_awaited()

    async def test_run_ai_tagging_for_story_generates_and_persists_tags(self, monkeypatch):
        story_id = uuid.uuid4()
        story = SimpleNamespace(
            id=story_id,
            title="Story Title",
            content="Story content",
            place_name="Istanbul",
            date_start=date(2024, 1, 1),
            date_end=date(2024, 12, 31),
            media_files=[SimpleNamespace(media_type="audio", transcript="Transcript text")],
        )

        session = AsyncMock()
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        monkeypatch.setattr("app.services.ai_tagging_system.is_ai_tagging_configured", lambda: True)
        monkeypatch.setattr("app.services.ai_tagging_system.AsyncSessionLocal", lambda: session)
        monkeypatch.setattr("app.services.ai_tagging_system._get_story_for_ai_tagging", AsyncMock(return_value=story))

        generate_mock = AsyncMock(return_value=["bogazici", "spor"])
        persist_mock = AsyncMock()
        monkeypatch.setattr("app.services.ai_tagging_system.generate_ai_story_tags", generate_mock)
        monkeypatch.setattr("app.services.ai_tagging_system.apply_ai_tags_to_story", persist_mock)

        result = await run_ai_tagging_for_story(story_id)

        assert result is True
        generate_mock.assert_awaited_once()
        persist_mock.assert_awaited_once_with(session, story_id, ["bogazici", "spor"])

    async def test_run_ai_tagging_for_story_includes_transcript_in_ai_content(self, monkeypatch):
        story_id = uuid.uuid4()
        story = SimpleNamespace(
            id=story_id,
            title="Story Title",
            content="Story content",
            place_name="Istanbul",
            date_start=date(2024, 1, 1),
            date_end=date(2024, 12, 31),
            media_files=[SimpleNamespace(media_type="audio", transcript="Transcript text")],
        )

        session = AsyncMock()
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        monkeypatch.setattr("app.services.ai_tagging_system.is_ai_tagging_configured", lambda: True)
        monkeypatch.setattr("app.services.ai_tagging_system.AsyncSessionLocal", lambda: session)
        monkeypatch.setattr("app.services.ai_tagging_system._get_story_for_ai_tagging", AsyncMock(return_value=story))

        generate_mock = AsyncMock(return_value=["bogazici"])
        persist_mock = AsyncMock()
        monkeypatch.setattr("app.services.ai_tagging_system.generate_ai_story_tags", generate_mock)
        monkeypatch.setattr("app.services.ai_tagging_system.apply_ai_tags_to_story", persist_mock)

        await run_ai_tagging_for_story(story_id)

        assert generate_mock.await_args.kwargs["content"] == "Story content\n\nAudio transcript:\nTranscript text"

    async def test_run_ai_tagging_for_story_retries_and_logs_without_raising(self, monkeypatch):
        story_id = uuid.uuid4()
        story = SimpleNamespace(
            id=story_id,
            title="Story Title",
            content="Story content",
            place_name="Istanbul",
            date_start=None,
            date_end=None,
            media_files=[],
        )

        session = AsyncMock()
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        monkeypatch.setattr("app.services.ai_tagging_system.is_ai_tagging_configured", lambda: True)
        monkeypatch.setattr("app.services.ai_tagging_system.AsyncSessionLocal", lambda: session)
        monkeypatch.setattr("app.services.ai_tagging_system._get_story_for_ai_tagging", AsyncMock(return_value=story))
        monkeypatch.setattr(
            "app.services.ai_tagging_system.generate_ai_story_tags",
            AsyncMock(side_effect=RuntimeError("boom")),
        )
        monkeypatch.setattr("app.services.ai_tagging_system.asyncio.sleep", AsyncMock())
        logger_exception = MagicMock()
        monkeypatch.setattr("app.services.ai_tagging_system.logger.exception", logger_exception)

        result = await run_ai_tagging_for_story(story_id)

        assert result is False
        assert logger_exception.call_count == 1
