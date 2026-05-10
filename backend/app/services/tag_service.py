import re
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.story import Story
from app.db.tag import Tag

MAX_TAG_LENGTH = 100
_TAG_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


def normalize_tag_name(tag: str) -> str:
    normalized = tag.strip().lower()
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Tags cannot be blank",
        )
    if len(normalized) > MAX_TAG_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Tags must be at most {MAX_TAG_LENGTH} characters long",
        )
    return normalized


def normalize_tag_list(tags: list[str] | None) -> list[str]:
    if not tags:
        return []

    normalized_tags: list[str] = []
    seen: set[str] = set()

    for tag in tags:
        normalized = normalize_tag_name(tag)
        if normalized not in seen:
            seen.add(normalized)
            normalized_tags.append(normalized)

    return normalized_tags


def build_tag_slug(tag_name: str) -> str:
    normalized_name = normalize_tag_name(tag_name)
    slug = _TAG_SLUG_PATTERN.sub("-", normalized_name).strip("-")
    return slug or normalized_name


async def get_or_create_tags(db: AsyncSession, tag_names: list[str] | None) -> list[Tag]:
    normalized_names = normalize_tag_list(tag_names)
    if not normalized_names:
        return []

    result = await db.execute(select(Tag).where(Tag.name.in_(normalized_names)))
    existing_tags = result.scalars().all()
    tags_by_name = {tag.name: tag for tag in existing_tags}

    missing_names = [name for name in normalized_names if name not in tags_by_name]
    new_tags = [Tag(name=name, slug=build_tag_slug(name)) for name in missing_names]

    for tag in new_tags:
        db.add(tag)

    if new_tags:
        await db.flush()

    new_tags_by_name = {tag.name: tag for tag in new_tags}
    return [tags_by_name.get(name) or new_tags_by_name[name] for name in normalized_names]


def attach_tags_to_story(story: Story, tags: list[Tag]) -> None:
    existing_tag_ids = {tag.id for tag in story.tags}
    for tag in tags:
        if tag.id not in existing_tag_ids:
            story.tags.append(tag)
            existing_tag_ids.add(tag.id)


async def apply_ai_tags_to_story(
    db: AsyncSession,
    story_id: uuid.UUID,
    tag_names: list[str] | None,
) -> Story:
    result = await db.execute(
        select(Story)
        .where(Story.id == story_id, Story.deleted_at.is_(None))
        .options(selectinload(Story.tags))
    )
    story = result.scalar_one_or_none()
    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found",
        )

    tags = await get_or_create_tags(db, tag_names)
    attach_tags_to_story(story, tags)
    await db.commit()
    await db.refresh(story, attribute_names=["tags"])
    return story
