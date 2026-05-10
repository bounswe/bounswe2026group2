import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import StoryStatus, StoryVisibility
from app.db.story import Story
from app.db.story_comment import StoryComment
from app.db.story_like import StoryLike
from app.db.story_save import StorySave
from app.db.user import User
from app.models.story import StoryResponse
from app.models.user import (
    UserDashboardResponse,
    UserEngagementStatsResponse,
    UserPublicProfileResponse,
    UserStoryListResponse,
)
from app.services.badge_service import get_user_badges
from app.services.storage import build_public_object_url


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

    row = (
        await db.execute(
            select(
                select(func.count(Story.id)).where(*story_filters).scalar_subquery().label("total_stories"),
                select(func.count(StoryLike.id))
                .select_from(StoryLike)
                .join(Story, StoryLike.story_id == Story.id)
                .where(*story_filters)
                .scalar_subquery()
                .label("total_likes_received"),
                select(func.count(StoryComment.id))
                .select_from(StoryComment)
                .join(Story, StoryComment.story_id == Story.id)
                .where(*story_filters)
                .scalar_subquery()
                .label("total_comments_received"),
                select(func.count(StorySave.id))
                .select_from(StorySave)
                .join(Story, StorySave.story_id == Story.id)
                .where(*story_filters)
                .scalar_subquery()
                .label("total_saves_received"),
            )
        )
    ).one()
    values = row._mapping

    return UserEngagementStatsResponse(
        total_stories=values["total_stories"],
        total_likes_received=values["total_likes_received"],
        total_comments_received=values["total_comments_received"],
        total_saves_received=values["total_saves_received"],
    )


async def get_current_user_dashboard(
    db: AsyncSession,
    current_user: User,
) -> UserDashboardResponse:
    story_filters = (
        Story.user_id == current_user.id,
        Story.deleted_at.is_(None),
    )
    saved_filters = (
        StorySave.user_id == current_user.id,
        Story.status == StoryStatus.PUBLISHED,
        Story.visibility == StoryVisibility.PUBLIC,
        Story.deleted_at.is_(None),
    )

    row = (
        await db.execute(
            select(
                select(func.count(Story.id)).where(*story_filters).scalar_subquery().label("stories_count"),
                select(func.count(Story.id))
                .select_from(Story)
                .join(StorySave, StorySave.story_id == Story.id)
                .where(*saved_filters)
                .scalar_subquery()
                .label("saved_count"),
                select(func.count(StoryLike.id))
                .select_from(StoryLike)
                .join(Story, StoryLike.story_id == Story.id)
                .where(*story_filters)
                .scalar_subquery()
                .label("total_likes_received"),
                select(func.count(StoryComment.id))
                .select_from(StoryComment)
                .join(Story, StoryComment.story_id == Story.id)
                .where(*story_filters)
                .scalar_subquery()
                .label("total_comments_received"),
                select(func.count(StorySave.id))
                .select_from(StorySave)
                .join(Story, StorySave.story_id == Story.id)
                .where(*story_filters)
                .scalar_subquery()
                .label("total_saves_received"),
            )
        )
    ).one()
    values = row._mapping

    return UserDashboardResponse(
        stories_count=values["stories_count"],
        saved_count=values["saved_count"],
        total_likes_received=values["total_likes_received"],
        total_comments_received=values["total_comments_received"],
        total_saves_received=values["total_saves_received"],
    )


async def get_user_public_profile(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> UserPublicProfileResponse:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    avatar_url = None
    if user.avatar_bucket_name and user.avatar_storage_key:
        avatar_url = build_public_object_url(
            bucket_name=user.avatar_bucket_name,
            storage_key=user.avatar_storage_key,
        )

    badges = await get_user_badges(db, user_id)
    return UserPublicProfileResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        bio=user.bio,
        location=user.location,
        avatar_url=avatar_url,
        badges=badges,
        created_at=user.created_at,
    )
