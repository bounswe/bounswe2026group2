import uuid
from datetime import date
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.enums import StoryStatus, StoryVisibility
from app.db.media_file import MediaFile
from app.db.story import Story
from app.db.story_like import StoryLike
from app.db.user import User
from app.models.story import (
    MediaFileResponse,
    MediaUploadRequest,
    MediaUploadResponse,
    StoryCreateRequest,
    StoryDetailResponse,
    StoryLikeResponse,
    StoryListResponse,
    StoryResponse,
    StoryUpdateRequest,
)
from app.services.storage import (
    build_public_object_url,
    delete_object,
    get_bucket_for_media_type,
    upload_bytes,
)

MAX_MEDIA_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB

ALLOWED_MIME_TYPES = {
    "image": {"image/jpeg", "image/png", "image/webp", "image/gif"},
    "audio": {"audio/mpeg", "audio/wav", "audio/ogg", "audio/mp4", "audio/webm"},
    "video": {"video/mp4", "video/webm", "video/quicktime"},
    "document": {
        "application/pdf",
        "text/plain",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    },
}


def _map_story_rows(rows: list[tuple[Story, str]]) -> StoryListResponse:
    stories = [StoryResponse.from_orm_with_author(story, author_username) for story, author_username in rows]
    return StoryListResponse(stories=stories, total=len(stories))


def _map_media_file(media: MediaFile) -> MediaFileResponse:
    return MediaFileResponse(
        id=media.id,
        story_id=media.story_id,
        bucket_name=media.bucket_name,
        storage_key=media.storage_key,
        media_url=build_public_object_url(
            bucket_name=media.bucket_name,
            storage_key=media.storage_key,
        ),
        original_filename=media.original_filename,
        mime_type=media.mime_type,
        media_type=media.media_type,
        file_size_bytes=media.file_size_bytes,
        sort_order=media.sort_order,
        alt_text=media.alt_text,
        caption=media.caption,
        created_at=media.created_at,
    )


def _map_story_detail(
    story: Story,
    author_username: str,
    like_count: int,
) -> StoryDetailResponse:
    story_response = StoryResponse.from_orm_with_author(story, author_username)
    media_files = [_map_media_file(media) for media in story.media_files]
    return StoryDetailResponse(
        **story_response.model_dump(),
        media_files=media_files,
        like_count=like_count,
    )


async def _get_story_like_count(db: AsyncSession, story_id: uuid.UUID) -> int:
    result = await db.execute(select(func.count(StoryLike.id)).where(StoryLike.story_id == story_id))
    return result.scalar_one()


def _validate_media_upload(file: UploadFile, payload: MediaUploadRequest) -> None:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    if not file.content_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content type is required",
        )

    allowed_for_type = ALLOWED_MIME_TYPES[payload.media_type.value]
    base_content_type = (file.content_type or "").split(";")[0].strip()
    if base_content_type not in allowed_for_type:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(f"Unsupported mime type '{base_content_type}' for media type '{payload.media_type.value}'"),
        )


def _build_media_storage_key(story_id: uuid.UUID, filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return f"stories/{story_id}/media/{uuid.uuid4()}{ext}"


async def list_available_stories(
    db: AsyncSession,
    min_lat: float | None = None,
    max_lat: float | None = None,
    min_lng: float | None = None,
    max_lng: float | None = None,
    query_start: date | None = None,
    query_end: date | None = None,
) -> StoryListResponse:
    stmt = (
        select(Story, User.username)
        .join(User, Story.user_id == User.id)
        .where(
            Story.status == StoryStatus.PUBLISHED,
            Story.visibility == StoryVisibility.PUBLIC,
        )
        .order_by(Story.created_at.desc())
    )

    if all(v is not None for v in (min_lat, max_lat, min_lng, max_lng)):
        stmt = stmt.where(
            Story.latitude.is_not(None),
            Story.longitude.is_not(None),
            Story.latitude >= min_lat,
            Story.latitude <= max_lat,
            Story.longitude >= min_lng,
            Story.longitude <= max_lng,
        )

    if query_start is not None and query_end is not None:
        stmt = stmt.where(
            Story.date_start.is_not(None),
            Story.date_end.is_not(None),
            Story.date_start <= query_end,
            Story.date_end >= query_start,
        )

    result = await db.execute(stmt)
    rows = result.all()

    return _map_story_rows(rows)


async def search_available_stories_by_place(
    db: AsyncSession,
    place_name: str,
    query_start: date | None = None,
    query_end: date | None = None,
) -> StoryListResponse:
    stmt = (
        select(Story, User.username)
        .join(User, Story.user_id == User.id)
        .where(
            Story.status == StoryStatus.PUBLISHED,
            Story.visibility == StoryVisibility.PUBLIC,
            Story.place_name.ilike(f"%{place_name}%"),
        )
        .order_by(Story.created_at.desc())
    )

    if query_start is not None and query_end is not None:
        stmt = stmt.where(
            Story.date_start.is_not(None),
            Story.date_end.is_not(None),
            Story.date_start <= query_end,
            Story.date_end >= query_start,
        )

    result = await db.execute(stmt)
    rows = result.all()

    return _map_story_rows(rows)


async def get_story_detail_by_id(
    db: AsyncSession,
    story_id: uuid.UUID,
) -> StoryDetailResponse:
    stmt = (
        select(Story, User.username)
        .join(User, Story.user_id == User.id)
        .where(Story.id == story_id)
        .options(selectinload(Story.media_files))
    )

    result = await db.execute(stmt)
    row = result.one_or_none()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found",
        )

    story, author_username = row
    like_count = await _get_story_like_count(db, story.id)
    return _map_story_detail(story, author_username, like_count)


async def create_story_with_location(
    db: AsyncSession,
    current_user: User,
    payload: StoryCreateRequest,
) -> StoryDetailResponse:
    place_name = payload.place_name.strip() if payload.place_name else None
    if not place_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="place_name is required for story location binding",
        )

    normalized_date_start, normalized_date_end, normalized_date_precision = payload.normalize_date_range()

    story = Story(
        user_id=current_user.id,
        title=payload.title,
        summary=payload.summary,
        content=payload.content,
        status=StoryStatus.PUBLISHED,
        visibility=StoryVisibility.PUBLIC,
        place_name=place_name,
        latitude=payload.latitude,
        longitude=payload.longitude,
        date_start=normalized_date_start,
        date_end=normalized_date_end,
        date_precision=normalized_date_precision,
    )

    db.add(story)
    await db.commit()
    await db.refresh(story)

    story_response = StoryResponse.from_orm_with_author(story, current_user.username)
    like_count = await _get_story_like_count(db, story.id)
    return StoryDetailResponse(**story_response.model_dump(), media_files=[], like_count=like_count)


async def update_story_with_location_and_dates(
    db: AsyncSession,
    story_id: uuid.UUID,
    current_user: User,
    payload: StoryUpdateRequest,
) -> StoryDetailResponse:
    story_result = await db.execute(select(Story).where(Story.id == story_id, Story.user_id == current_user.id))
    story = story_result.scalar_one_or_none()
    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found",
        )

    place_name = payload.place_name.strip() if payload.place_name else None
    if not place_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="place_name is required for story location binding",
        )

    normalized_date_start, normalized_date_end, normalized_date_precision = payload.normalize_date_range()

    story.title = payload.title
    story.summary = payload.summary
    story.content = payload.content
    story.place_name = place_name
    story.latitude = payload.latitude
    story.longitude = payload.longitude
    story.date_start = normalized_date_start
    story.date_end = normalized_date_end
    story.date_precision = normalized_date_precision

    await db.commit()
    await db.refresh(story)

    story_response = StoryResponse.from_orm_with_author(story, current_user.username)
    like_count = await _get_story_like_count(db, story.id)
    return StoryDetailResponse(**story_response.model_dump(), media_files=[], like_count=like_count)


async def like_story(
    db: AsyncSession,
    story_id: uuid.UUID,
    current_user: User,
) -> StoryLikeResponse:
    story_result = await db.execute(select(Story.id).where(Story.id == story_id))
    story_exists = story_result.scalar_one_or_none()
    if story_exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found",
        )

    existing_like_result = await db.execute(
        select(StoryLike).where(
            StoryLike.story_id == story_id,
            StoryLike.user_id == current_user.id,
        )
    )
    existing_like = existing_like_result.scalar_one_or_none()

    if existing_like is None:
        db.add(
            StoryLike(
                story_id=story_id,
                user_id=current_user.id,
            )
        )
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()

    like_count = await _get_story_like_count(db, story_id)
    return StoryLikeResponse(
        story_id=story_id,
        liked=True,
        like_count=like_count,
    )


async def unlike_story(
    db: AsyncSession,
    story_id: uuid.UUID,
    current_user: User,
) -> StoryLikeResponse:
    story_result = await db.execute(select(Story.id).where(Story.id == story_id))
    story_exists = story_result.scalar_one_or_none()
    if story_exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found",
        )

    existing_like_result = await db.execute(
        select(StoryLike).where(
            StoryLike.story_id == story_id,
            StoryLike.user_id == current_user.id,
        )
    )
    existing_like = existing_like_result.scalar_one_or_none()

    if existing_like is not None:
        await db.delete(existing_like)
        await db.commit()

    like_count = await _get_story_like_count(db, story_id)
    return StoryLikeResponse(
        story_id=story_id,
        liked=False,
        like_count=like_count,
    )


async def upload_media_for_story(
    db: AsyncSession,
    story_id: uuid.UUID,
    file: UploadFile,
    payload: MediaUploadRequest,
) -> MediaUploadResponse:
    _validate_media_upload(file, payload)

    story_result = await db.execute(select(Story).where(Story.id == story_id))
    story = story_result.scalar_one_or_none()
    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    file_size = len(file_bytes)
    if file_size > MAX_MEDIA_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds {MAX_MEDIA_UPLOAD_BYTES} bytes",
        )

    bucket_name = get_bucket_for_media_type(payload.media_type)
    storage_key = _build_media_storage_key(story_id, file.filename)

    try:
        upload_bytes(
            bucket_name=bucket_name,
            storage_key=storage_key,
            content=file_bytes,
            content_type=file.content_type,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to upload media to storage",
        )

    media = MediaFile(
        story_id=story_id,
        bucket_name=bucket_name,
        storage_key=storage_key,
        original_filename=file.filename,
        mime_type=file.content_type,
        media_type=payload.media_type,
        file_size_bytes=file_size,
        sort_order=payload.sort_order,
        alt_text=payload.alt_text,
        caption=payload.caption,
    )

    try:
        db.add(media)
        await db.commit()
        await db.refresh(media)
    except Exception:
        await db.rollback()
        try:
            delete_object(bucket_name=bucket_name, storage_key=storage_key)
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist media metadata",
        )

    return MediaUploadResponse(media=_map_media_file(media))
