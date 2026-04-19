import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, Enum, Float, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.enums import DatePrecision, StoryStatus, StoryVisibility
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.media_file import MediaFile
    from app.db.story_comment import StoryComment
    from app.db.story_like import StoryLike
    from app.db.story_save import StorySave
    from app.db.user import User


class Story(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "stories"
    __table_args__ = (
        Index("ix_stories_user_id", "user_id"),
        Index("ix_stories_status", "status"),
        Index("ix_stories_visibility", "visibility"),
        CheckConstraint(
            "date_end IS NULL OR date_start IS NULL OR date_end >= date_start",
            name="ck_stories_date_range_valid",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[StoryStatus] = mapped_column(
        Enum(StoryStatus, name="story_status", native_enum=False),
        nullable=False,
        default=StoryStatus.DRAFT,
        server_default=text("'draft'"),
    )
    visibility: Mapped[StoryVisibility] = mapped_column(
        Enum(StoryVisibility, name="story_visibility", native_enum=False),
        nullable=False,
        default=StoryVisibility.PRIVATE,
        server_default=text("'private'"),
    )

    place_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    date_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_precision: Mapped[DatePrecision | None] = mapped_column(
        Enum(DatePrecision, name="date_precision", native_enum=False),
        nullable=True,
    )

    user: Mapped["User"] = relationship(back_populates="stories")
    media_files: Mapped[list["MediaFile"]] = relationship(
        back_populates="story",
        cascade="all, delete-orphan",
    )
    saves: Mapped[list["StorySave"]] = relationship(
        back_populates="story",
        cascade="all, delete-orphan",
    )
    comments: Mapped[list["StoryComment"]] = relationship(
        back_populates="story",
        cascade="all, delete-orphan",
    )

    story_likes: Mapped[list["StoryLike"]] = relationship(
        back_populates="story",
        cascade="all, delete-orphan",
    )
