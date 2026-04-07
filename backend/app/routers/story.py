import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.enums import MediaType
from app.db.session import get_db
from app.db.user import User
from app.models.story import (
    MediaUploadRequest,
    MediaUploadResponse,
    StoryBoundsFilter,
    StoryCreateRequest,
    StoryDetailResponse,
    StoryListResponse,
    StoryUpdateRequest,
)
from app.services.story_service import (
    create_story_with_location,
    get_story_detail_by_id,
    list_available_stories,
    search_available_stories_by_place,
    update_story_with_location_and_dates,
    upload_media_for_story,
)

router = APIRouter(prefix="/stories", tags=["stories"])


@router.post(
    "",
    response_model=StoryDetailResponse,
    status_code=status.HTTP_201_CREATED,
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
    responses={
        401: {"description": "Missing or invalid authentication token"},
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


@router.get("", response_model=StoryListResponse)
async def list_stories(
    min_lat: float | None = Query(default=None),
    max_lat: float | None = Query(default=None),
    min_lng: float | None = Query(default=None),
    max_lng: float | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    try:
        bounds = StoryBoundsFilter(
            min_lat=min_lat,
            max_lat=max_lat,
            min_lng=min_lng,
            max_lng=max_lng,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors())

    return await list_available_stories(
        db,
        min_lat=bounds.min_lat,
        max_lat=bounds.max_lat,
        min_lng=bounds.min_lng,
        max_lng=bounds.max_lng,
    )


@router.get("/search", response_model=StoryListResponse)
async def search_stories(
    place_name: str = Query(min_length=1, max_length=255),
    db: AsyncSession = Depends(get_db),
):
    return await search_available_stories_by_place(db, place_name)


@router.get(
    "/{story_id}",
    response_model=StoryDetailResponse,
    responses={404: {"description": "Story not found"}},
)
async def get_story_by_id(
    story_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await get_story_detail_by_id(db, story_id)


@router.post(
    "/{story_id}/media",
    response_model=MediaUploadResponse,
    status_code=status.HTTP_201_CREATED,
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