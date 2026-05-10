import json
from collections.abc import Mapping

import httpx

from app.core.config import settings
from app.services.tag_service import normalize_tag_list

MAX_GENERATED_TAGS = 10
MIN_GENERATED_TAGS = 5
AI_REQUEST_TIMEOUT_SECONDS = 30.0


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
        "messages": [
            {
                "role": "system",
                "content": "You generate clean keyword tags for story discovery.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }


async def generate_ai_story_tags(
    *,
    title: str,
    content: str,
    place_name: str | None = None,
    date_label: str | None = None,
) -> list[str]:
    if not settings.AI_TAGGING_API_URL:
        raise ValueError("AI_TAGGING_API_URL is not configured")
    if not settings.AI_TAGGING_API_KEY:
        raise ValueError("AI_TAGGING_API_KEY is not configured")

    payload = build_ai_tagging_request_payload(
        title=title,
        content=content,
        place_name=place_name,
        date_label=date_label,
    )
    headers = {
        "Authorization": f"Bearer {settings.AI_TAGGING_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=AI_REQUEST_TIMEOUT_SECONDS) as client:
        response = await client.post(
            settings.AI_TAGGING_API_URL,
            json=payload,
            headers=headers,
        )
        response.raise_for_status()

    tags = parse_ai_generated_tags(response.json())
    return tags[:MAX_GENERATED_TAGS]
