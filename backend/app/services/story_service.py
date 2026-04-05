from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import StoryStatus, StoryVisibility
from app.db.story import Story
from app.db.user import User
from app.models.story import StoryListResponse, StoryResponse


def _build_date_label(date_start: int | None, date_end: int | None) -> str | None:
    if date_start is not None and date_end is not None:
        return f"{date_start} - {date_end}"
    if date_start is not None:
        return str(date_start)
    return None


async def list_available_stories(db: AsyncSession) -> StoryListResponse:
    stmt = (
        select(Story, User.username)
        .join(User, Story.user_id == User.id)
        .where(
            Story.status == StoryStatus.PUBLISHED,
            Story.visibility == StoryVisibility.PUBLIC,
        )
        .order_by(Story.created_at.desc())
    )

    result = await db.execute(stmt)
    rows = result.all()

    stories = [
        StoryResponse(
            id=story.id,
            title=story.title,
            summary=story.summary,
            content=story.content,
            author=author_username,
            place_name=story.place_name,
            latitude=story.latitude,
            longitude=story.longitude,
            date_start=story.date_start,
            date_end=story.date_end,
            date_label=_build_date_label(story.date_start, story.date_end),
            status=story.status,
            visibility=story.visibility,
            created_at=story.created_at,
        )
        for story, author_username in rows
    ]

    return StoryListResponse(stories=stories, total=len(stories))