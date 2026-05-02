import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.enums import NotificationEventType
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.story import Story
    from app.db.story_comment import StoryComment
    from app.db.user import User


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_recipient_created_at", "recipient_user_id", "created_at"),
        Index("ix_notifications_actor_user_id", "actor_user_id"),
        Index("ix_notifications_story_id", "story_id"),
        Index("ix_notifications_comment_id", "comment_id"),
    )

    recipient_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    actor_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    story_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stories.id", ondelete="CASCADE"),
        nullable=False,
    )
    comment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("story_comments.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[NotificationEventType] = mapped_column(
        Enum(NotificationEventType, name="notification_event_type", native_enum=False),
        nullable=False,
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    recipient_user: Mapped["User"] = relationship(
        back_populates="received_notifications",
        foreign_keys=[recipient_user_id],
    )
    actor_user: Mapped["User"] = relationship(
        back_populates="triggered_notifications",
        foreign_keys=[actor_user_id],
    )
    story: Mapped["Story"] = relationship(back_populates="notifications")
    comment: Mapped["StoryComment | None"] = relationship(back_populates="notifications")
