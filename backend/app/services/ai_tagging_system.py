import asyncio
import json
import logging
import uuid
from collections.abc import Mapping

from google import genai
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.enums import MediaType
from app.db.media_file import MediaFile
from app.db.session import AsyncSessionLocal
from app.db.story import Story
from app.services.tag_service import apply_ai_tags_to_story, normalize_tag_list

MAX_GENERATED_TAGS = 10
MIN_GENERATED_TAGS = 5
AI_TAGGING_MAX_ATTEMPTS = 3
AI_TAGGING_RETRY_DELAYS_SECONDS = (1.0, 2.0)

logger = logging.getLogger(__name__)


def is_ai_tagging_configured() -> bool:
    return bool(settings.GEMINI_API_KEY or settings.AI_TAGGING_API_KEY)


def build_ai_tagging_prompt(
    *,
    title: str,
    content: str,
    place_name: str | None = None,
    date_label: str | None = None,
) -> str:
    location_line = place_name or "Unknown"
    date_line = date_label or "Unknown"

    return (
        "You are generating keyword tags for a location-based story-sharing application.\n"
        "Users share stories connected to specific places and times.\n"
        "Return 5 to 10 short, useful tags in English.\n"
        "Prioritize location, historical period/date, core topic, and important themes from the story.\n"
        "Keep tags lowercase, concise, and search-friendly.\n"
        "Do not include explanations.\n"
        'Return valid JSON with this shape only: {"tags": ["tag1", "tag2"]}\n\n'
        f"Story title: {title}\n"
        f"Location: {location_line}\n"
        f"Date: {date_line}\n"
        "Story content:\n"
        f"{content}"
    )


def _extract_candidate_text(response_payload: object) -> str:
    if isinstance(response_payload, str):
        return response_payload

    response_text = getattr(response_payload, "text", None)
    if isinstance(response_text, str):
        return response_text

    if not isinstance(response_payload, Mapping):
        raise ValueError("Unsupported AI response payload")

    if isinstance(response_payload.get("tags"), list):
        return json.dumps({"tags": response_payload["tags"]})

    choices = response_payload.get("choices")
    if isinstance(choices, list) and choices:
        first_choice = choices[0]
        if isinstance(first_choice, Mapping):
            message = first_choice.get("message")
            if isinstance(message, Mapping) and isinstance(message.get("content"), str):
                return message["content"]
            if isinstance(first_choice.get("text"), str):
                return first_choice["text"]

    if isinstance(response_payload.get("content"), str):
        return response_payload["content"]

    raise ValueError("Could not extract AI response text")


def parse_ai_generated_tags(response_payload: object) -> list[str]:
    candidate_text = _extract_candidate_text(response_payload).strip()
    if not candidate_text:
        return []

    try:
        parsed_payload = json.loads(candidate_text)
    except json.JSONDecodeError:
        parts = [part.strip() for part in candidate_text.replace("\n", ",").split(",")]
        return normalize_tag_list([part for part in parts if part])

    if isinstance(parsed_payload, list):
        return normalize_tag_list([str(item) for item in parsed_payload])

    if isinstance(parsed_payload, Mapping):
        tags = parsed_payload.get("tags", [])
        if not isinstance(tags, list):
            raise ValueError("AI response 'tags' field must be a list")
        return normalize_tag_list([str(item) for item in tags])

    raise ValueError("Unsupported parsed AI response payload")


def build_ai_tagging_request_payload(
    *,
    title: str,
    content: str,
    place_name: str | None = None,
    date_label: str | None = None,
) -> dict[str, object]:
    prompt = build_ai_tagging_prompt(
        title=title,
        content=content,
        place_name=place_name,
        date_label=date_label,
    )
    return {
        "model": settings.AI_TAGGING_MODEL,
        "contents": prompt,
    }


def _create_gemini_client() -> genai.Client:
    if not is_ai_tagging_configured():
        raise ValueError("GEMINI_API_KEY is not configured")
    api_key = settings.GEMINI_API_KEY or settings.AI_TAGGING_API_KEY
    return genai.Client(api_key=api_key)


def _generate_ai_story_tags_sync(
    *,
    title: str,
    content: str,
    place_name: str | None = None,
    date_label: str | None = None,
) -> list[str]:
    payload = build_ai_tagging_request_payload(
        title=title,
        content=content,
        place_name=place_name,
        date_label=date_label,
    )
    client = _create_gemini_client()
    try:
        response = client.models.generate_content(
            model=payload["model"],
            contents=payload["contents"],
        )
    finally:
        client.close()

    tags = parse_ai_generated_tags(response)
    return tags[:MAX_GENERATED_TAGS]


async def generate_ai_story_tags(
    *,
    title: str,
    content: str,
    place_name: str | None = None,
    date_label: str | None = None,
) -> list[str]:
    return await asyncio.to_thread(
        _generate_ai_story_tags_sync,
        title=title,
        content=content,
        place_name=place_name,
        date_label=date_label,
    )


def _build_story_date_label(story: Story) -> str | None:
    if story.date_start and story.date_end:
        if story.date_start == story.date_end:
            return story.date_start.isoformat()
        return f"{story.date_start.isoformat()} - {story.date_end.isoformat()}"
    if story.date_start:
        return story.date_start.isoformat()
    return None


def _collect_story_transcript_text(media_files: list[MediaFile]) -> str | None:
    transcript_parts = [
        media.transcript.strip() for media in media_files if media.transcript and media.transcript.strip()
    ]
    if not transcript_parts:
        return None
    return "\n\n".join(transcript_parts)


def _story_requires_transcript_before_tagging(story: Story) -> bool:
    return any(media.media_type == MediaType.AUDIO for media in story.media_files)


def trigger_ai_tagging_if_ready(story: Story) -> bool:
    if not (story.content and story.content.strip()):
        return False

    if not _story_requires_transcript_before_tagging(story):
        return True

    audio_files = [media for media in story.media_files if media.media_type == MediaType.AUDIO]
    return all(media.transcript and media.transcript.strip() for media in audio_files)


async def _get_story_for_ai_tagging(story_id: uuid.UUID, db) -> Story | None:
    result = await db.execute(
        select(Story).where(Story.id == story_id, Story.deleted_at.is_(None)).options(selectinload(Story.media_files))
    )
    return result.scalar_one_or_none()


async def run_ai_tagging_for_story(story_id: uuid.UUID) -> bool:
    if not is_ai_tagging_configured():
        return False

    async with AsyncSessionLocal() as db:
        story = await _get_story_for_ai_tagging(story_id, db)
        if story is None or not trigger_ai_tagging_if_ready(story):
            return False

        transcript_text = _collect_story_transcript_text(story.media_files)
        content = story.content.strip()
        if transcript_text:
            content = f"{content}\n\nAudio transcript:\n{transcript_text}"

        for attempt in range(AI_TAGGING_MAX_ATTEMPTS):
            try:
                generated_tags = await generate_ai_story_tags(
                    title=story.title,
                    content=content,
                    place_name=story.place_name,
                    date_label=_build_story_date_label(story),
                )
                await apply_ai_tags_to_story(db, story.id, generated_tags)
                return True
            except Exception:
                if attempt == AI_TAGGING_MAX_ATTEMPTS - 1:
                    logger.exception(
                        "AI tagging failed for story %s after %s attempts", story.id, AI_TAGGING_MAX_ATTEMPTS
                    )
                    return False

                await asyncio.sleep(AI_TAGGING_RETRY_DELAYS_SECONDS[attempt])

        return False
