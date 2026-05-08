from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.db.user import User
from app.models.user import UserDashboardResponse, UserEngagementStatsResponse, UserStoryListResponse
from app.services.user_service import (
    get_current_user_dashboard,
    get_current_user_engagement_stats,
    list_current_user_saved_stories,
    list_current_user_stories,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me/stories",
    response_model=UserStoryListResponse,
    summary="List current user's stories",
    description=(
        "Return a paginated list of stories created by the authenticated user, "
        "including private or draft stories. Soft-deleted stories are excluded."
    ),
    responses={
        401: {"description": "Missing or invalid authentication token"},
        422: {"description": "Validation error for pagination parameters"},
    },
)
async def list_my_stories(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_current_user_stories(
        db,
        current_user,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/me/saved",
    response_model=UserStoryListResponse,
    summary="List current user's saved stories",
    description=(
        "Return a paginated list of stories bookmarked by the authenticated user. "
        "Only stories that are still public, published, and not soft-deleted are included."
    ),
    responses={
        401: {"description": "Missing or invalid authentication token"},
        422: {"description": "Validation error for pagination parameters"},
    },
)
async def list_my_saved_stories(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_current_user_saved_stories(
        db,
        current_user,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/me/stats",
    response_model=UserEngagementStatsResponse,
    summary="Get current user engagement stats",
    description=(
        "Return aggregate engagement statistics for the authenticated user's non-deleted stories: "
        "story count, likes received, comments received, and saves received."
    ),
    responses={
        401: {"description": "Missing or invalid authentication token"},
    },
)
async def get_my_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_current_user_engagement_stats(db, current_user)


@router.get(
    "/me/dashboard",
    response_model=UserDashboardResponse,
    summary="Get current user dashboard summary",
    description=(
        "Return a summary card for the authenticated user's dashboard, combining created-story count, "
        "currently visible saved-story count, and top engagement metrics."
    ),
    responses={
        401: {"description": "Missing or invalid authentication token"},
    },
)
async def get_my_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_current_user_dashboard(db, current_user)
