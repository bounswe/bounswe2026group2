from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import StoryStatus, StoryVisibility
from app.db.story import Story
from app.db.story_comment import StoryComment
from app.db.story_like import StoryLike
from app.db.story_save import StorySave
from app.db.user import User
from app.models.story import StoryResponse
from app.models.user import UserDashboardResponse, UserEngagementStatsResponse, UserStoryListResponse


def _map_user_story_rows(
    rows: list[tuple[Story, str]],
    *,
    total: int,
    limit: int,
    offset: int,
) -> UserStoryListResponse:
    stories = [StoryResponse.from_orm_with_author(story, author_username) for story, author_username in rows]
    return UserStoryListResponse(
        stories=stories,
        total=total,
        limit=limit,
        offset=offset,
    )


async def list_current_user_stories(
    db: AsyncSession,
    current_user: User,
    *,
    limit: int,
    offset: int,
) -> UserStoryListResponse:
    total_result = await db.execute(
        select(func.count(Story.id)).where(
            Story.user_id == current_user.id,
            Story.deleted_at.is_(None),
        )
    )
    total = total_result.scalar_one()

    rows_result = await db.execute(
        select(Story, User.username)
        .join(User, Story.user_id == User.id)
        .where(
            Story.user_id == current_user.id,
            Story.deleted_at.is_(None),
        )
        .order_by(Story.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    return _map_user_story_rows(rows_result.all(), total=total, limit=limit, offset=offset)


async def list_current_user_saved_stories(
    db: AsyncSession,
    current_user: User,
    *,
    limit: int,
    offset: int,
) -> UserStoryListResponse:
    filters = (
        StorySave.user_id == current_user.id,
        Story.status == StoryStatus.PUBLISHED,
        Story.visibility == StoryVisibility.PUBLIC,
        Story.deleted_at.is_(None),
    )

    total_result = await db.execute(
        select(func.count(Story.id)).select_from(Story).join(StorySave, StorySave.story_id == Story.id).where(*filters)
    )
    total = total_result.scalar_one()

    rows_result = await db.execute(
        select(Story, User.username)
        .join(StorySave, StorySave.story_id == Story.id)
        .join(User, Story.user_id == User.id)
        .where(*filters)
        .order_by(StorySave.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    return _map_user_story_rows(rows_result.all(), total=total, limit=limit, offset=offset)


async def get_current_user_engagement_stats(
    db: AsyncSession,
    current_user: User,
) -> UserEngagementStatsResponse:
    story_filters = (
        Story.user_id == current_user.id,
        Story.deleted_at.is_(None),
    )

    total_stories_result = await db.execute(select(func.count(Story.id)).where(*story_filters))
    total_likes_result = await db.execute(
        select(func.count(StoryLike.id))
        .select_from(StoryLike)
        .join(Story, StoryLike.story_id == Story.id)
        .where(*story_filters)
    )
    total_comments_result = await db.execute(
        select(func.count(StoryComment.id))
        .select_from(StoryComment)
        .join(Story, StoryComment.story_id == Story.id)
        .where(*story_filters)
    )
    total_saves_result = await db.execute(
        select(func.count(StorySave.id))
        .select_from(StorySave)
        .join(Story, StorySave.story_id == Story.id)
        .where(*story_filters)
    )

    return UserEngagementStatsResponse(
        total_stories=total_stories_result.scalar_one(),
        total_likes_received=total_likes_result.scalar_one(),
        total_comments_received=total_comments_result.scalar_one(),
        total_saves_received=total_saves_result.scalar_one(),
    )


async def get_current_user_dashboard(
    db: AsyncSession,
    current_user: User,
) -> UserDashboardResponse:
    stats = await get_current_user_engagement_stats(db, current_user)

    saved_count_result = await db.execute(
        select(func.count(Story.id))
        .select_from(Story)
        .join(StorySave, StorySave.story_id == Story.id)
        .where(
            StorySave.user_id == current_user.id,
            Story.status == StoryStatus.PUBLISHED,
            Story.visibility == StoryVisibility.PUBLIC,
            Story.deleted_at.is_(None),
        )
    )
    saved_count = saved_count_result.scalar_one()

    return UserDashboardResponse(
        stories_count=stats.total_stories,
        saved_count=saved_count,
        total_likes_received=stats.total_likes_received,
        total_comments_received=stats.total_comments_received,
        total_saves_received=stats.total_saves_received,
    )
