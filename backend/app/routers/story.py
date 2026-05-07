import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.enums import MediaType, ReportStatus
from app.db.session import get_db
from app.db.user import User
from app.models.comment import CommentCreateRequest, CommentListResponse, CommentResponse
from app.models.story import (
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
)
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_story_with_location(db, current_user, payload)


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
    file: UploadFile = File(...),
    media_type: MediaType = Form(...),
    alt_text: str | None = Form(default=None),
    caption: str | None = Form(default=None),
    sort_order: int = Form(default=0),
    _current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payload = MediaUploadRequest(
        media_type=media_type,
        alt_text=alt_text,
        caption=caption,
        sort_order=sort_order,
    )
    return await upload_media_for_story(db, story_id, file, payload)


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
    tags=["admin"],
    summary="Get reported stories",
)
def get_reported_stories(
    status: ReportStatus | None = Query(None, description="Filter by report status"),
    db: AsyncSession = Depends(get_db),
):
    query = db.query(StoryReport)
    if status:
        query = query.filter(StoryReport.status == status)
    reports = query.all()
    return reports
