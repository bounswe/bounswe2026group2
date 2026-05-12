import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.db.enums import ReportStatus, UserRole
from app.db.story import Story
from app.db.story_report import StoryReport
from app.db.user import User
from app.models.story import AdminReportListItem, AdminReportsListResponse, StoryReportResponse, UpdateReportStatusRequest


def ensure_admin_user(current_user: User) -> None:
    """Require the current user to have admin privileges."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


async def list_admin_reports(
    db: AsyncSession,
    report_status: ReportStatus | None = None,
) -> AdminReportsListResponse:
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

    if report_status:
        query = query.where(StoryReport.status == report_status)

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


async def update_report_status_as_admin(
    db: AsyncSession,
    report_id: uuid.UUID,
    payload: UpdateReportStatusRequest,
) -> StoryReportResponse:
    result = await db.execute(select(StoryReport).where(StoryReport.id == report_id))
    report = result.scalars().first()

    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    if payload.status == ReportStatus.REMOVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use the admin remove story endpoint to mark reports as removed",
        )

    if report.status == ReportStatus.REMOVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Removed reports cannot be updated",
        )

    report.status = payload.status
    db.add(report)
    await db.commit()
    await db.refresh(report)

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
