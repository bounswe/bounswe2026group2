import uuid

from app.db.enums import StoryStatus, StoryVisibility
from app.db.story import Story

# Fixed default coordinates: Çeliktepe, Istanbul — used as the primary
# demo location and kept constant so map-related tests are deterministic.
DEFAULT_TITLE = "A Story from Çeliktepe"
DEFAULT_CONTENT = "Children used to play in the narrow streets between the gecekondu houses."
DEFAULT_SUMMARY = "A childhood memory from the Çeliktepe neighbourhood of Istanbul."
DEFAULT_PLACE_NAME = "Çeliktepe, Istanbul"
DEFAULT_LATITUDE = 41.0739
DEFAULT_LONGITUDE = 28.9606
DEFAULT_DATE_START = 1960
DEFAULT_DATE_END = 1980


def make_story_payload(
    *,
    title: str = DEFAULT_TITLE,
    content: str = DEFAULT_CONTENT,
    summary: str | None = DEFAULT_SUMMARY,
    place_name: str = DEFAULT_PLACE_NAME,
    latitude: float = DEFAULT_LATITUDE,
    longitude: float = DEFAULT_LONGITUDE,
    date_start: int | None = DEFAULT_DATE_START,
    date_end: int | None = DEFAULT_DATE_END,
    suffix: int | str | None = None,
) -> dict:
    """Return a dict that matches StoryCreateRequest, for use in API-level tests."""
    if suffix is not None:
        title = f"{title} {suffix}"
        place_name = f"{place_name} {suffix}"
    payload = {
        "title": title,
        "content": content,
        "place_name": place_name,
        "latitude": latitude,
        "longitude": longitude,
    }
    if summary is not None:
        payload["summary"] = summary
    if date_start is not None:
        payload["date_start"] = date_start
    if date_end is not None:
        payload["date_end"] = date_end
    return payload


def make_story_update_payload(
    *,
    title: str = "An Updated Story from Çeliktepe",
    content: str = "The neighbourhood changed a lot after the 1980s.",
    summary: str | None = "An updated memory from Çeliktepe.",
    place_name: str = DEFAULT_PLACE_NAME,
    latitude: float = DEFAULT_LATITUDE,
    longitude: float = DEFAULT_LONGITUDE,
    date_start: int | None = DEFAULT_DATE_START,
    date_end: int | None = DEFAULT_DATE_END,
) -> dict:
    """Return a dict that matches StoryUpdateRequest, for use in update API tests."""
    payload = {
        "title": title,
        "content": content,
        "place_name": place_name,
        "latitude": latitude,
        "longitude": longitude,
    }
    if summary is not None:
        payload["summary"] = summary
    if date_start is not None:
        payload["date_start"] = date_start
    if date_end is not None:
        payload["date_end"] = date_end
    return payload


def make_story_entity(
    *,
    user_id: uuid.UUID,
    title: str = DEFAULT_TITLE,
    content: str = DEFAULT_CONTENT,
    summary: str | None = DEFAULT_SUMMARY,
    place_name: str | None = DEFAULT_PLACE_NAME,
    latitude: float | None = DEFAULT_LATITUDE,
    longitude: float | None = DEFAULT_LONGITUDE,
    date_start: int | None = DEFAULT_DATE_START,
    date_end: int | None = DEFAULT_DATE_END,
    status: StoryStatus = StoryStatus.PUBLISHED,
    visibility: StoryVisibility = StoryVisibility.PUBLIC,
    suffix: int | str | None = None,
) -> Story:
    """Return a Story ORM object for direct insertion into a test DB session."""
    if suffix is not None:
        title = f"{title} {suffix}"
        if place_name is not None:
            place_name = f"{place_name} {suffix}"
    return Story(
        user_id=user_id,
        title=title,
        content=content,
        summary=summary,
        place_name=place_name,
        latitude=latitude,
        longitude=longitude,
        date_start=date_start,
        date_end=date_end,
        status=status,
        visibility=visibility,
    )
