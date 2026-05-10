import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.enums import MediaType, NotificationEventType, ReportStatus, StoryStatus, StoryVisibility
from app.db.media_file import MediaFile
from app.db.notification import Notification
from app.db.story import Story
from app.db.story_comment import StoryComment
from app.db.story_like import StoryLike
from app.db.story_report import StoryReport
from app.db.story_save import StorySave
from app.db.user import User
from app.models.comment import CommentAuthorResponse, CommentCreateRequest, CommentListResponse, CommentResponse
from app.models.story import (
    MediaFileResponse,
    MediaUploadRequest,
    MediaUploadResponse,
    StoryCreateRequest,
    StoryDetailResponse,
    StoryLikeResponse,
    StoryListResponse,
    StoryReportRequest,
    StoryReportResponse,
    StoryResponse,
    StorySaveResponse,
    StoryUpdateRequest,
)
from app.services.media_validation import read_uploaded_file_content, validate_media_upload
from app.services.storage import (
    build_public_object_url,
    delete_object,
    get_bucket_for_media_type,
    upload_bytes,
)
from app.services.transcription_service import transcribe_media_file


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
        transcript=media.transcript,
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


async def get_story_like_summary(
    db: AsyncSession,
    story_id: uuid.UUID,
    current_user: User,
) -> StoryLikeResponse:
    await _get_story_or_404(db, story_id)

    existing_like_result = await db.execute(
        select(StoryLike).where(
            StoryLike.story_id == story_id,
            StoryLike.user_id == current_user.id,
        )
    )
    existing_like = existing_like_result.scalar_one_or_none()
    like_count = await _get_story_like_count(db, story_id)

    return StoryLikeResponse(
        story_id=story_id,
        liked=existing_like is not None,
        like_count=like_count,
    )


def _map_comment_row(comment: StoryComment, author: User) -> CommentResponse:
    return CommentResponse(
        id=comment.id,
        story_id=comment.story_id,
        content=comment.content,
        author=CommentAuthorResponse(
            id=author.id,
            username=author.username,
            display_name=author.display_name,
        ),
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


def _build_media_storage_key(story_id: uuid.UUID, filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return f"stories/{story_id}/media/{uuid.uuid4()}{ext}"


async def _get_story_or_404(
    db: AsyncSession,
    story_id: uuid.UUID,
) -> Story:
    story_result = await db.execute(select(Story).where(Story.id == story_id, Story.deleted_at.is_(None)))
    story = story_result.scalar_one_or_none()
    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found",
        )
    return story


def _queue_story_interaction_notification(
    db: AsyncSession,
    *,
    story: Story,
    actor: User,
    event_type: NotificationEventType,
    comment_id: uuid.UUID | None = None,
) -> None:
    # Duplicate likes/saves are ignored at the interaction-table level; notifications
    # are only queued when a new interaction row is actually being created.
    if story.user_id == actor.id:
        return

    db.add(
        Notification(
            recipient_user_id=story.user_id,
            actor_user_id=actor.id,
            story_id=story.id,
            comment_id=comment_id,
            event_type=event_type,
        )
    )


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
            Story.deleted_at.is_(None),
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
            Story.deleted_at.is_(None),
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
        .where(Story.id == story_id, Story.deleted_at.is_(None))
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


async def list_comments_for_story(
    db: AsyncSession,
    story_id: uuid.UUID,
) -> CommentListResponse:
    await _get_story_or_404(db, story_id)

    stmt = (
        select(StoryComment, User)
        .join(User, StoryComment.user_id == User.id)
        .where(StoryComment.story_id == story_id)
        .order_by(StoryComment.created_at.asc(), StoryComment.id.asc())
    )
    result = await db.execute(stmt)
    rows = result.all()
    comments = [_map_comment_row(comment, author) for comment, author in rows]
    return CommentListResponse(comments=comments, total=len(comments))


async def create_comment_for_story(
    db: AsyncSession,
    story_id: uuid.UUID,
    current_user: User,
    payload: CommentCreateRequest,
) -> CommentResponse:
    story = await _get_story_or_404(db, story_id)

    comment = StoryComment(
        story_id=story_id,
        user_id=current_user.id,
        content=payload.content,
    )
    db.add(comment)
    await db.flush()
    _queue_story_interaction_notification(
        db,
        story=story,
        actor=current_user,
        event_type=NotificationEventType.STORY_COMMENTED,
        comment_id=comment.id,
    )
    await db.commit()
    await db.refresh(comment)

    return _map_comment_row(comment, current_user)


async def delete_comment_for_story(
    db: AsyncSession,
    story_id: uuid.UUID,
    comment_id: uuid.UUID,
    current_user: User,
) -> None:
    await _get_story_or_404(db, story_id)

    comment_result = await db.execute(
        select(StoryComment).where(
            StoryComment.id == comment_id,
            StoryComment.story_id == story_id,
        )
    )
    comment = comment_result.scalar_one_or_none()
    if comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    if comment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to delete this comment",
        )

    await db.delete(comment)
    await db.commit()


async def save_story_for_user(
    db: AsyncSession,
    story_id: uuid.UUID,
    current_user: User,
) -> StorySaveResponse:
    story = await _get_story_or_404(db, story_id)

    existing_save_result = await db.execute(
        select(StorySave).where(
            StorySave.story_id == story_id,
            StorySave.user_id == current_user.id,
        )
    )
    existing_save = existing_save_result.scalar_one_or_none()

    if existing_save is None:
        db.add(StorySave(story_id=story_id, user_id=current_user.id))
        _queue_story_interaction_notification(
            db,
            story=story,
            actor=current_user,
            event_type=NotificationEventType.STORY_BOOKMARKED,
        )
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()

    return StorySaveResponse(story_id=story_id, saved=True)


async def unsave_story_for_user(
    db: AsyncSession,
    story_id: uuid.UUID,
    current_user: User,
) -> StorySaveResponse:
    await _get_story_or_404(db, story_id)

    existing_save_result = await db.execute(
        select(StorySave).where(
            StorySave.story_id == story_id,
            StorySave.user_id == current_user.id,
        )
    )
    existing_save = existing_save_result.scalar_one_or_none()

    if existing_save is not None:
        await db.delete(existing_save)
        await db.commit()

    return StorySaveResponse(story_id=story_id, saved=False)


async def list_saved_stories_for_user(
    db: AsyncSession,
    current_user: User,
) -> StoryListResponse:
    stmt = (
        select(Story, User.username)
        .join(StorySave, StorySave.story_id == Story.id)
        .join(User, Story.user_id == User.id)
        .where(
            StorySave.user_id == current_user.id,
            Story.status == StoryStatus.PUBLISHED,
            Story.visibility == StoryVisibility.PUBLIC,
            Story.deleted_at.is_(None),
        )
        .order_by(StorySave.created_at.desc())
    )

    result = await db.execute(stmt)
    rows = result.all()
    return _map_story_rows(rows)


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
        is_anonymous=payload.is_anonymous,
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
    story_result = await db.execute(
        select(Story).where(
            Story.id == story_id,
            Story.user_id == current_user.id,
            Story.deleted_at.is_(None),
        )
    )
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
    if payload.is_anonymous is not None:
        story.is_anonymous = payload.is_anonymous

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
    story = await _get_story_or_404(db, story_id)

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
        _queue_story_interaction_notification(
            db,
            story=story,
            actor=current_user,
            event_type=NotificationEventType.STORY_LIKED,
        )
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()

    return await get_story_like_summary(db, story_id, current_user)


async def unlike_story(
    db: AsyncSession,
    story_id: uuid.UUID,
    current_user: User,
) -> StoryLikeResponse:
    await _get_story_or_404(db, story_id)

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

    return await get_story_like_summary(db, story_id, current_user)


async def upload_media_for_story(
    db: AsyncSession,
    story_id: uuid.UUID,
    file: UploadFile,
    payload: MediaUploadRequest,
    background_tasks: BackgroundTasks | None = None,
) -> MediaUploadResponse:
    normalized_content_type = validate_media_upload(file, payload.media_type)

    story_result = await db.execute(select(Story).where(Story.id == story_id, Story.deleted_at.is_(None)))
    story = story_result.scalar_one_or_none()
    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found",
        )

    file_bytes = await read_uploaded_file_content(file)
    file_size = len(file_bytes)

    bucket_name = get_bucket_for_media_type(payload.media_type)
    storage_key = _build_media_storage_key(story_id, file.filename)

    try:
        upload_bytes(
            bucket_name=bucket_name,
            storage_key=storage_key,
            content=file_bytes,
            content_type=normalized_content_type,
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
        mime_type=normalized_content_type,
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

    if payload.media_type == MediaType.AUDIO and background_tasks is not None:
        background_tasks.add_task(
            transcribe_media_file,
            media_file_id=media.id,
            filename=file.filename,
            content=file_bytes,
            mime_type=normalized_content_type,
        )

    return MediaUploadResponse(media=_map_media_file(media))


_EARTH_RADIUS_KM = 6371.0


async def get_nearby_stories(
    db: AsyncSession,
    center_lat: float,
    center_lng: float,
    radius_km: float = 10.0,
) -> StoryListResponse:
    lat1 = func.radians(center_lat)
    lat2 = func.radians(Story.latitude)
    lon1 = func.radians(center_lng)
    lon2 = func.radians(Story.longitude)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = func.pow(func.sin(dlat / 2), 2) + func.cos(lat1) * func.cos(lat2) * func.pow(func.sin(dlon / 2), 2)
    distance_km = func.asin(func.sqrt(a)) * (_EARTH_RADIUS_KM * 2)

    stmt = (
        select(Story, User.username)
        .join(User, Story.user_id == User.id)
        .where(
            Story.status == StoryStatus.PUBLISHED,
            Story.visibility == StoryVisibility.PUBLIC,
            Story.deleted_at.is_(None),
            Story.latitude.is_not(None),
            Story.longitude.is_not(None),
            distance_km <= radius_km,
        )
        .order_by(distance_km)
    )

    result = await db.execute(stmt)
    rows = result.all()

    return _map_story_rows(rows)


async def create_report_for_story(
    db: AsyncSession,
    story_id: uuid.UUID,
    current_user: User,
    payload: StoryReportRequest,
) -> StoryReportResponse:
    # Check if story exists
    story_result = await db.execute(select(Story).where(Story.id == story_id, Story.deleted_at.is_(None)))
    story = story_result.scalar_one_or_none()
    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found",
        )

    # Create report
    report = StoryReport(
        story_id=story_id,
        user_id=current_user.id,
        reason=payload.reason,
        description=payload.description,
    )

    # Ensure report fields are populated correctly
    report.id = uuid.uuid4()
    report.status = ReportStatus.PENDING
    report.created_at = datetime.now(timezone.utc)

    db.add(report)

    try:
        await db.commit()
        await db.refresh(report)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already reported this story",
        )

    return StoryReportResponse.model_validate(report)


async def remove_story_as_admin(
    db: AsyncSession,
    story_id: uuid.UUID,
    current_user: User,
) -> None:
    story_result = await db.execute(select(Story).where(Story.id == story_id, Story.deleted_at.is_(None)))
    story = story_result.scalar_one_or_none()
    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found",
        )

    story.deleted_at = datetime.now(timezone.utc)
    story.deleted_by = current_user.id
    db.add(story)

    reports_result = await db.execute(
        select(StoryReport).where(
            StoryReport.story_id == story_id,
            StoryReport.status == ReportStatus.PENDING,
        )
    )
    pending_reports = reports_result.scalars().all()
    for report in pending_reports:
        report.status = ReportStatus.REMOVED
        db.add(report)

    await db.commit()
