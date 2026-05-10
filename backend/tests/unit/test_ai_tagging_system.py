from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai_tagging_system import (
    build_ai_tagging_prompt,
    build_ai_tagging_request_payload,
    generate_ai_story_tags,
    parse_ai_generated_tags,
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

        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][1]["role"] == "user"
        assert payload["response_format"] == {"type": "json_object"}


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

    def test_parse_ai_generated_tags_falls_back_to_comma_separated_text(self):
        tags = parse_ai_generated_tags("Bogazici, Turkey, Sports")

        assert tags == ["bogazici", "turkey", "sports"]


@pytest.mark.asyncio
class TestGenerateStoryTagsWithAi:
    async def test_generate_ai_story_tags_posts_and_parses_response(self, monkeypatch):
        monkeypatch.setattr("app.services.ai_tagging_system.settings.AI_TAGGING_API_URL", "https://example.com/tagging")
        monkeypatch.setattr("app.services.ai_tagging_system.settings.AI_TAGGING_API_KEY", "secret")
        monkeypatch.setattr("app.services.ai_tagging_system.settings.AI_TAGGING_MODEL", "fake-model")

        response = MagicMock()
        response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"tags": ["Bogazici", "Turkiye", "Spor"]}',
                    }
                }
            ]
        }
        response.raise_for_status.return_value = None

        post = AsyncMock(return_value=response)

        with patch("app.services.ai_tagging_system.httpx.AsyncClient") as client_cls:
            client = AsyncMock()
            client.post = post
            client.__aenter__.return_value = client
            client.__aexit__.return_value = None
            client_cls.return_value = client

            tags = await generate_ai_story_tags(
                title="A Day in Bogazici",
                content="A sports memory from Istanbul.",
                place_name="Istanbul",
                date_label="1998",
            )

        assert tags == ["bogazici", "turkiye", "spor"]
        post.assert_awaited_once()

    async def test_generate_ai_story_tags_requires_configuration(self, monkeypatch):
        monkeypatch.setattr("app.services.ai_tagging_system.settings.AI_TAGGING_API_URL", "")
        monkeypatch.setattr("app.services.ai_tagging_system.settings.AI_TAGGING_API_KEY", "")

        with pytest.raises(ValueError) as exc_info:
            await generate_ai_story_tags(title="Title", content="Content")

        assert "AI_TAGGING_API_URL" in str(exc_info.value)
