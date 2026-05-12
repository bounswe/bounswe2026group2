import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.enums import ReportReason, ReportStatus
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.story import Story
    from app.db.user import User


class StoryReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "story_reports"
    __table_args__ = (
        UniqueConstraint("story_id", "user_id", name="uq_story_reports_story_user"),
        Index("ix_story_reports_story_id", "story_id"),
        Index("ix_story_reports_user_id", "user_id"),
        Index("ix_story_reports_status", "status"),
    )

    story_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stories.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    reason: Mapped[ReportReason] = mapped_column(
        Enum(ReportReason, name="report_reason", native_enum=False),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, name="report_status", native_enum=False),
        nullable=False,
        default=ReportStatus.PENDING,
        server_default=text("'pending'"),
    )

    story: Mapped["Story"] = relationship(back_populates="reports")
    user: Mapped["User"] = relationship(back_populates="reports")
