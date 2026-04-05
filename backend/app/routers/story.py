import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.enums import MediaType
from app.db.session import get_db
from app.db.user import User
from app.models.story import (
    MediaUploadRequest,
    MediaUploadResponse,
    StoryDetailResponse,
    StoryListResponse,
)
from app.services.story_service import (
    get_story_detail_by_id,
    list_available_stories,
    search_available_stories_by_place,
    upload_media_for_story,
)

router = APIRouter(prefix="/stories", tags=["stories"])


@router.get("", response_model=StoryListResponse)
async def list_stories(db: AsyncSession = Depends(get_db)):
    return await list_available_stories(db)


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