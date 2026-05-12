import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.enums import ReportStatus
from app.db.session import get_db
from app.db.user import User
from app.models.story import AdminReportsListResponse, StoryReportResponse, UpdateReportStatusRequest
from app.services.admin_service import (
    ensure_admin_user,
    list_admin_reports,
    remove_story_as_admin,
    update_report_status_as_admin,
)

router = APIRouter(prefix="/stories/admin", tags=["admin"])


async def get_admin_context(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> tuple[User, AsyncSession]:
    ensure_admin_user(current_user)
    return current_user, db


@router.get(
    "/reports",
    response_model=AdminReportsListResponse,
    summary="Get reported stories (admin only)",
    description="Retrieve all reported stories with filtering options. Admin access required.",
    responses={
        401: {"description": "Missing or invalid authentication token"},
        403: {"description": "User is not an admin"},
    },
)
async def get_admin_reports(
    report_status: ReportStatus | None = Query(None, alias="status", description="Filter by report status"),
    context: tuple[User, AsyncSession] = Depends(get_admin_context),
):
    _, db = context
    return await list_admin_reports(db, report_status=report_status)


@router.put(
    "/reports/{report_id}",
    response_model=StoryReportResponse,
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
    context: tuple[User, AsyncSession] = Depends(get_admin_context),
):
    _, db = context
    return await update_report_status_as_admin(db, report_id, payload)


@router.delete(
    "/stories/{story_id}",
    status_code=status.HTTP_204_NO_CONTENT,
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
    context: tuple[User, AsyncSession] = Depends(get_admin_context),
):
    current_user, db = context
    await remove_story_as_admin(db, story_id, current_user)
