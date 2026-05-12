import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.db.enums import ReportReason, ReportStatus, UserRole


class AdminReportListItem(BaseModel):
    """Report with related story and user information for admin view."""

    id: uuid.UUID
    story_id: uuid.UUID
    user_id: uuid.UUID
    reason: ReportReason
    description: str | None
    status: ReportStatus
    created_at: datetime
    story_title: str | None = None
    story_author_user_id: uuid.UUID | None = None
    story_author_username: str | None = None
    reported_user_id: uuid.UUID | None = None
    reported_username: str | None = None
    reporter_username: str | None = None

    model_config = {"from_attributes": True}


class AdminReportsListResponse(BaseModel):
    """Response for admin reports listing."""

    total: int
    reports: list[AdminReportListItem]


class UpdateReportStatusRequest(BaseModel):
    """Request to update report status."""

    status: ReportStatus = Field(..., description="New status for the report")


class AdminUserRestrictionResponse(BaseModel):
    """Restricted-state response for admin user moderation actions."""

    id: uuid.UUID
    username: str
    email: str
    role: UserRole
    is_restricted: bool

    model_config = {"from_attributes": True}
