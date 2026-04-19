from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.enums import UserRole
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.story import Story
    from app.db.story_comment import StoryComment
    from app.db.story_like import StoryLike
    from app.db.story_save import StorySave


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("username", name="uq_users_username"),
        UniqueConstraint("email", name="uq_users_email"),
    )

    username: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=False),
        nullable=False,
        default=UserRole.USER,
        server_default=text("'user'"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    stories: Mapped[list["Story"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    saved_stories: Mapped[list["StorySave"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    comments: Mapped[list["StoryComment"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    story_likes: Mapped[list["StoryLike"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
