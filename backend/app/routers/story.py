import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.enums import MediaType, ReportStatus, UserRole
from app.db.session import get_db
from app.db.story import Story
from app.db.story_report import StoryReport
from app.db.user import User
from app.models.comment import CommentCreateRequest, CommentListResponse, CommentResponse
from app.models.story import (
    AdminReportListItem,
    AdminReportsListResponse,
    MediaUploadRequest,
    MediaUploadResponse,
    StoryBoundsFilter,
    StoryCreateRequest,
    StoryDateRangeFilter,
    StoryDetailResponse,
    StoryLikeResponse,
    StoryListResponse,
    StoryReportRequest,
    StoryReportResponse,
    StorySaveResponse,
    StoryUpdateRequest,
    UpdateReportStatusRequest,
)
from app.services.ai_tagging_system import is_ai_tagging_configured, run_ai_tagging_for_story
from app.services.story_service import (
    create_comment_for_story,
    create_report_for_story,
    create_story_with_location,
    delete_comment_for_story,
    get_nearby_stories,
    get_story_detail_by_id,
    get_story_like_summary,
    like_story,
    list_available_stories,
    list_comments_for_story,
    list_saved_stories_for_user,
    remove_story_as_admin,
    save_story_for_user,
    search_available_stories_by_place,
    unlike_story,
    unsave_story_for_user,
    update_story_with_location_and_dates,
    upload_media_for_story,
)

router = APIRouter(prefix="/stories", tags=["stories"])


@router.post(
    "",
    response_model=StoryDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a story",
    description="Create a new story tied to a geographic location and historical date range. Requires authentication.",
    responses={
        401: {"description": "Missing or invalid authentication token"},
        422: {"description": "Validation error for story/location input"},
    },
)
async def create_story(
    payload: StoryCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    story = await create_story_with_location(db, current_user, payload)
    if is_ai_tagging_configured():
        background_tasks.add_task(run_ai_tagging_for_story, story.id)
    return story


@router.put(
    "/{story_id}",
    response_model=StoryDetailResponse,
    summary="Update a story",
    description="Update an existing story. Only the story owner may update it. Requires authentication.",
    responses={
        401: {"description": "Missing or invalid authentication token"},
        403: {"description": "Authenticated user is not the story owner"},
        404: {"description": "Story not found"},
        422: {"description": "Validation error for story/location input"},
    },
)
async def update_story(
    story_id: uuid.UUID,
    payload: StoryUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await update_story_with_location_and_dates(db, story_id, current_user, payload)


@router.get(
    "",
    response_model=StoryListResponse,
    summary="List public stories",
    description=(
        "Return all published public stories. Optionally filter by geographic bounding box "
        "(min_lat/max_lat/min_lng/max_lng) and/or date range (query_start/query_end/query_precision). "
        "query_precision accepts 'year' or 'date'."
    ),
    responses={
        422: {"description": "Validation error for bounds or date filter parameters"},
    },
)
async def list_stories(
    min_lat: float | None = Query(default=None),
    max_lat: float | None = Query(default=None),
    min_lng: float | None = Query(default=None),
    max_lng: float | None = Query(default=None),
    query_start: int | str | None = Query(default=None),
    query_end: int | str | None = Query(default=None),
    query_precision: str | None = Query(default=None),
    tags: list[str] | None = Query(
        default=None,
        description="Filter by one or more story tags. Repeat the parameter for multiple tags.",
    ),
    db: AsyncSession = Depends(get_db),
):
    try:
        bounds = StoryBoundsFilter(
            min_lat=min_lat,
            max_lat=max_lat,
            min_lng=min_lng,
            max_lng=max_lng,
        )
        date_filter = StoryDateRangeFilter(
            query_start=query_start,
            query_end=query_end,
            query_precision=query_precision,
        )
        normalized_query_start, normalized_query_end, _ = date_filter.normalize_query_range()
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=exc.errors(include_context=False, include_url=False),
        )

    return await list_available_stories(
        db,
        min_lat=bounds.min_lat,
        max_lat=bounds.max_lat,
        min_lng=bounds.min_lng,
        max_lng=bounds.max_lng,
        query_start=normalized_query_start,
        query_end=normalized_query_end,
        tags=tags,
    )


@router.get(
    "/search",
    response_model=StoryListResponse,
    summary="Search stories by place name",
    description=(
        "Search published public stories by place name (case-insensitive substring match). "
        "Optionally filter by date range using query_start/query_end/query_precision."
    ),
    responses={
        422: {"description": "Validation error for place_name or date filter parameters"},
    },
)
async def search_stories(
    place_name: str = Query(min_length=1, max_length=255),
    query_start: int | str | None = Query(default=None),
    query_end: int | str | None = Query(default=None),
    query_precision: str | None = Query(default=None),
    tags: list[str] | None = Query(
        default=None,
        description="Filter by one or more story tags. Repeat the parameter for multiple tags.",
    ),
    db: AsyncSession = Depends(get_db),
):
    try:
        date_filter = StoryDateRangeFilter(
            query_start=query_start,
            query_end=query_end,
            query_precision=query_precision,
        )
        normalized_query_start, normalized_query_end, _ = date_filter.normalize_query_range()
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=exc.errors(include_context=False, include_url=False),
        )

    return await search_available_stories_by_place(
        db,
        place_name,
        query_start=normalized_query_start,
        query_end=normalized_query_end,
        tags=tags,
    )


@router.get(
    "/saved",
    response_model=StoryListResponse,
    summary="List saved stories",
    description="Return the authenticated user's saved stories that are still published and public.",
    responses={
        401: {"description": "Missing or invalid authentication token"},
    },
)
async def list_saved_stories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_saved_stories_for_user(db, current_user)


@router.get(
    "/nearby",
    response_model=StoryListResponse,
    summary="List stories near a location",
    description=(
        "Return published public stories within a given radius of a coordinate point, "
        "ordered by distance ascending (nearest first). "
        "lat and lng are required. radius_km defaults to 10 km (max 500 km)."
    ),
    responses={
        422: {"description": "Validation error for lat, lng, or radius_km"},
    },
)
async def list_nearby_stories(
    lat: float = Query(ge=-90.0, le=90.0),
    lng: float = Query(ge=-180.0, le=180.0),
    radius_km: float = Query(default=10.0, gt=0.0, le=500.0),
    db: AsyncSession = Depends(get_db),
):
    return await get_nearby_stories(db, center_lat=lat, center_lng=lng, radius_km=radius_km)


@router.get(
    "/{story_id}",
    response_model=StoryDetailResponse,
    summary="Get story by ID",
    description="Return the full detail of a single story including its media files.",
    responses={
        404: {"description": "Story not found"},
    },
)
async def get_story_by_id(
    story_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await get_story_detail_by_id(db, story_id)


@router.get(
    "/{story_id}/comments",
    response_model=CommentListResponse,
    summary="List comments for a story",
    description="Return story comments in chronological order.",
    responses={
        404: {"description": "Story not found"},
    },
)
async def list_story_comments(
    story_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await list_comments_for_story(db, story_id)


@router.post(
    "/{story_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a comment on a story",
    description="Create a comment as the authenticated user.",
    responses={
        401: {"description": "Missing or invalid authentication token"},
        404: {"description": "Story not found"},
        422: {"description": "Validation error for comment payload"},
    },
)
async def create_story_comment(
    story_id: uuid.UUID,
    payload: CommentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_comment_for_story(db, story_id, current_user, payload)


@router.delete(
    "/{story_id}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a comment",
    description="Delete a comment owned by the authenticated user.",
    responses={
        401: {"description": "Missing or invalid authentication token"},
        403: {"description": "Authenticated user does not own the comment"},
        404: {"description": "Story or comment not found"},
    },
)
async def delete_story_comment(
    story_id: uuid.UUID,
    comment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await delete_comment_for_story(db, story_id, comment_id, current_user)


@router.get(
    "/{story_id}/like",
    response_model=StoryLikeResponse,
    summary="Get story like summary",
    description="Return whether the authenticated user has liked the story and the story's current like count.",
    responses={
        401: {"description": "Missing or invalid authentication token"},
        404: {"description": "Story not found"},
    },
)
async def get_story_like_by_id(
    story_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_story_like_summary(db, story_id, current_user)


@router.post(
    "/{story_id}/like",
    response_model=StoryLikeResponse,
    summary="Like a story",
    description="Like a story as the authenticated user. Repeating the request keeps the story liked.",
    responses={
        401: {"description": "Missing or invalid authentication token"},
        404: {"description": "Story not found"},
    },
)
async def like_story_by_id(
    story_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await like_story(db, story_id, current_user)


@router.delete(
    "/{story_id}/like",
    response_model=StoryLikeResponse,
    summary="Unlike a story",
    description="Remove the authenticated user's like from a story. Repeating the request keeps the story unliked.",
    responses={
        401: {"description": "Missing or invalid authentication token"},
        404: {"description": "Story not found"},
    },
)
async def unlike_story_by_id(
    story_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await unlike_story(db, story_id, current_user)


@router.post(
    "/{story_id}/save",
    response_model=StorySaveResponse,
    summary="Save a story",
    description="Save a story for the authenticated user. Repeating the request keeps the story saved.",
    responses={
        401: {"description": "Missing or invalid authentication token"},
        404: {"description": "Story not found"},
    },
)
async def save_story(
    story_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await save_story_for_user(db, story_id, current_user)


@router.delete(
    "/{story_id}/save",
    response_model=StorySaveResponse,
    summary="Remove a saved story",
    description="Remove a saved story for the authenticated user. Repeating the request keeps the story unsaved.",
    responses={
        401: {"description": "Missing or invalid authentication token"},
        404: {"description": "Story not found"},
    },
)
async def unsave_story(
    story_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await unsave_story_for_user(db, story_id, current_user)


@router.post(
    "/{story_id}/media",
    response_model=MediaUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload media for a story",
    description=(
        "Attach an image, audio, or video file to a story. Maximum file size is 20 MB. Requires authentication."
    ),
    responses={
        401: {"description": "Missing or invalid authentication token"},
        404: {"description": "Story not found"},
        413: {"description": "File exceeds the 20 MB size limit"},
        502: {"description": "Object storage backend unavailable"},
    },
)
async def upload_story_media(
    story_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    media_type: MediaType = Form(...),
    alt_text: str | None = Form(default=None),
    caption: str | None = Form(default=None),
    transcript: str | None = Form(default=None),
    sort_order: int = Form(default=0),
    _current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payload = MediaUploadRequest(
        media_type=media_type,
        alt_text=alt_text,
        caption=caption,
        transcript=transcript,
        sort_order=sort_order,
    )
    return await upload_media_for_story(
        db,
        story_id,
        file,
        payload,
        background_tasks=background_tasks,
    )


@router.post(
    "/{story_id}/report",
    response_model=StoryReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Report a story",
    description="Report a story as inappropriate or problematic. Duplicate reports from the same user are rejected.",
    responses={
        401: {"description": "Missing or invalid authentication token"},
        404: {"description": "Story not found"},
        409: {"description": "User has already reported this story"},
        422: {"description": "Validation error for report payload"},
    },
)
async def report_story(
    story_id: uuid.UUID,
    payload: StoryReportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_report_for_story(db, story_id, current_user, payload)


@router.get(
    "/admin/reports",
    response_model=AdminReportsListResponse,
    tags=["admin"],
    summary="Get reported stories (admin only)",
    description="Retrieve all reported stories with filtering options. Admin access required.",
    responses={
        401: {"description": "Missing or invalid authentication token"},
        403: {"description": "User is not an admin"},
    },
)
async def get_admin_reports(
    status: ReportStatus | None = Query(None, description="Filter by report status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Admin check
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Build query with joins to get related data for both the reporter and story author.
    from sqlalchemy import select
    from sqlalchemy.orm import aliased

    story_author = aliased(User)
    reporter = aliased(User)

    query = (
        select(
            StoryReport.id,
            StoryReport.story_id,
            StoryReport.user_id,
            StoryReport.reason,
            StoryReport.description,
            StoryReport.status,
            StoryReport.created_at,
            Story.title.label("story_title"),
            story_author.username.label("story_author_username"),
            reporter.username.label("reporter_username"),
        )
        .join(Story, StoryReport.story_id == Story.id)
        .join(story_author, Story.user_id == story_author.id)
        .join(reporter, StoryReport.user_id == reporter.id)
    )

    if status:
        query = query.where(StoryReport.status == status)

    query = query.order_by(StoryReport.created_at.desc())

    result = await db.execute(query)
    rows = result.fetchall()

    reports = [
        AdminReportListItem(
            id=row.id,
            story_id=row.story_id,
            user_id=row.user_id,
            reason=row.reason,
            description=row.description,
            status=row.status,
            created_at=row.created_at,
            story_title=row.story_title,
            reporter_username=row.reporter_username,
            story_author_username=row.story_author_username,
        )
        for row in rows
    ]

    return AdminReportsListResponse(total=len(reports), reports=reports)


@router.put(
    "/admin/reports/{report_id}",
    response_model=StoryReportResponse,
    tags=["admin"],
    summary="Update report status (admin only)",
    description="Mark a reported story as reviewed. Story removal is handled by the admin remove-story endpoint.",
    responses={
        401: {"description": "Missing or invalid authentication token"},
        400: {"description": "Invalid report status transition"},
        403: {"description": "User is not an admin"},
        404: {"description": "Report not found"},
        409: {"description": "Report can no longer be updated"},
    },
)
async def update_report_status(
    report_id: uuid.UUID,
    payload: UpdateReportStatusRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Admin check
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Fetch the report
    from sqlalchemy import select

    query = select(StoryReport).where(StoryReport.id == report_id)
    result = await db.execute(query)
    report = result.scalars().first()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if payload.status == ReportStatus.REMOVED:
        raise HTTPException(
            status_code=400,
            detail="Use the admin remove story endpoint to mark reports as removed",
        )

    if report.status == ReportStatus.REMOVED:
        raise HTTPException(
            status_code=409,
            detail="Removed reports cannot be updated",
        )

    # MVP moderation flow: this endpoint is only for acknowledging a report as reviewed.
    report.status = payload.status
    db.add(report)
    await db.commit()
    await db.refresh(report)

    return report


@router.delete(
    "/admin/stories/{story_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["admin"],
    summary="Remove story (admin only)",
    description="Soft-delete a story and mark its pending reports as removed. Admin access required.",
    responses={
        401: {"description": "Missing or invalid authentication token"},
        403: {"description": "User is not an admin"},
        404: {"description": "Story not found"},
    },
)
async def admin_remove_story(
    story_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    await remove_story_as_admin(db, story_id, current_user)
