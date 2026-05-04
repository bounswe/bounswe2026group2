import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.story import Story
    from app.db.user import User


class StorySave(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "story_saves"
    __table_args__ = (
        UniqueConstraint("story_id", "user_id", name="uq_story_saves_story_user"),
        Index("ix_story_saves_story_id", "story_id"),
        Index("ix_story_saves_user_id", "user_id"),
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

    story: Mapped["Story"] = relationship(back_populates="saves")
    user: Mapped["User"] = relationship(back_populates="saved_stories")
