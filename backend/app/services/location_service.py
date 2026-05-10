import uuid

from fastapi import HTTPException, status

from app.db.story import Story
from app.db.story_location import StoryLocation
from app.models.story import LocationInput


def validate_location_list(locations: list[LocationInput]) -> None:
    seen: set[tuple[float, float]] = set()
    for loc in locations:
        key = (loc.latitude, loc.longitude)
        if key in seen:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Duplicate coordinates in locations list: ({loc.latitude}, {loc.longitude})",
            )
        seen.add(key)


def build_story_locations(story_id: uuid.UUID, locations: list[LocationInput]) -> list[StoryLocation]:
    return [
        StoryLocation(
            story_id=story_id,
            latitude=loc.latitude,
            longitude=loc.longitude,
            label=loc.label.strip() if loc.label else None,
            sort_order=i,
        )
        for i, loc in enumerate(locations)
    ]


def replace_story_locations(story: Story, locations: list[LocationInput]) -> None:
    validate_location_list(locations)
    story.locations.clear()
    new_locs = build_story_locations(story.id, locations)
    story.locations.extend(new_locs)
