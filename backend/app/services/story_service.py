from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import StoryStatus, StoryVisibility
from app.db.story import Story
from app.db.user import User
from app.models.story import StoryListResponse, StoryResponse


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

    stories = [StoryResponse.from_orm_with_author(story, author_username) for story, author_username in rows]

    return StoryListResponse(stories=stories, total=len(stories))