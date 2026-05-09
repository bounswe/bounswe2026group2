import uuid
from datetime import date

from app.db.enums import DatePrecision, StoryStatus, StoryVisibility
from app.db.story import Story

# Fixed default coordinates: Çeliktepe, Istanbul — used as the primary
# demo location and kept constant so map-related tests are deterministic.
DEFAULT_TITLE = "A Story from Çeliktepe"
DEFAULT_CONTENT = "Children used to play in the narrow streets between the gecekondu houses."
DEFAULT_SUMMARY = "A childhood memory from the Çeliktepe neighbourhood of Istanbul."
DEFAULT_PLACE_NAME = "Çeliktepe, Istanbul"
DEFAULT_LATITUDE = 41.0739
DEFAULT_LONGITUDE = 28.9606

# Payload defaults: integers, because StoryCreateRequest accepts year integers
# and normalises them internally before writing to the DB.
DEFAULT_DATE_START = 1960
DEFAULT_DATE_END = 1980

# Entity defaults: full date objects, because the Story ORM column is DATE.
# Year-precision stories are stored as Jan 1 (start) and Dec 31 (end).
DEFAULT_ENTITY_DATE_START = date(1960, 1, 1)
DEFAULT_ENTITY_DATE_END = date(1980, 12, 31)


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
    is_anonymous: bool = False,
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
        "is_anonymous": is_anonymous,
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
    date_start: date | None = DEFAULT_ENTITY_DATE_START,
    date_end: date | None = DEFAULT_ENTITY_DATE_END,
    date_precision: DatePrecision | None = DatePrecision.YEAR,
    status: StoryStatus = StoryStatus.PUBLISHED,
    visibility: StoryVisibility = StoryVisibility.PUBLIC,
    is_anonymous: bool = False,
    suffix: int | str | None = None,
) -> Story:
    """Return a Story ORM object for direct insertion into a test DB session.

    date_start and date_end must be Python date objects matching the DATE
    column type. Use year-precision stories as: date(1960, 1, 1) / date(1980, 12, 31).
    The payload factories (make_story_payload) accept integers — that is correct
    because StoryCreateRequest normalises them before writing to the DB.
    """
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
        date_precision=date_precision,
        status=status,
        visibility=visibility,
        is_anonymous=is_anonymous,
    )
