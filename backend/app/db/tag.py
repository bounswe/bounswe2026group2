import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Table, Column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

story_tags_table = Table(
    "story_tags",
    Base.metadata,
    Column(
        "story_id",
        UUID(as_uuid=True),
        ForeignKey("stories.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "tag_id",
        UUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Index("ix_story_tags_story_id", "story_id"),
    Index("ix_story_tags_tag_id", "tag_id"),
)

if TYPE_CHECKING:
    from app.db.story import Story


class Tag(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tags"
    __table_args__ = (
        Index("ix_tags_name", "name"),
        Index("ix_tags_slug", "slug"),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)

    stories: Mapped[list["Story"]] = relationship(
        secondary=story_tags_table,
        back_populates="tags",
    )
