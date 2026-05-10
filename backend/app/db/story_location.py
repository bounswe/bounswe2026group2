import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.story import Story


class StoryLocation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "story_locations"
    __table_args__ = (
        Index("ix_story_locations_story_id", "story_id"),
        Index("ix_story_locations_coords", "latitude", "longitude"),
        CheckConstraint(
            "latitude >= -90.0 AND latitude <= 90.0",
            name="ck_story_locations_latitude",
        ),
        CheckConstraint(
            "longitude >= -180.0 AND longitude <= 180.0",
            name="ck_story_locations_longitude",
        ),
    )

    story_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stories.id", ondelete="CASCADE"),
        nullable=False,
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    story: Mapped["Story"] = relationship(back_populates="locations")
