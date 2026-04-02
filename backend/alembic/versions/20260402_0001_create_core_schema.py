"""Create initial user, story, and media file tables.

Revision ID: 20260402_0001
Revises:
Create Date: 2026-04-02 00:01:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "20260402_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


user_role_enum = sa.Enum(
    "user",
    "admin",
    name="user_role",
    native_enum=False,
)
story_status_enum = sa.Enum(
    "draft",
    "published",
    "archived",
    name="story_status",
    native_enum=False,
)
story_visibility_enum = sa.Enum(
    "private",
    "public",
    "unlisted",
    name="story_visibility",
    native_enum=False,
)
media_type_enum = sa.Enum(
    "image",
    "audio",
    "video",
    "document",
    name="media_type",
    native_enum=False,
)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "users",
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("role", user_role_enum, nullable=False, server_default=sa.text("'user'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("username", name="uq_users_username"),
    )

    op.create_table(
        "stories",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "status",
            story_status_enum,
            nullable=False,
            server_default=sa.text("'draft'"),
        ),
        sa.Column(
            "visibility",
            story_visibility_enum,
            nullable=False,
            server_default=sa.text("'private'"),
        ),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stories_status", "stories", ["status"], unique=False)
    op.create_index("ix_stories_user_id", "stories", ["user_id"], unique=False)
    op.create_index("ix_stories_visibility", "stories", ["visibility"], unique=False)

    op.create_table(
        "media_files",
        sa.Column(
            "story_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("bucket_name", sa.String(length=63), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("media_type", media_type_enum, nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("alt_text", sa.Text(), nullable=True),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "file_size_bytes >= 0",
            name="ck_media_files_file_size_non_negative",
        ),
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "bucket_name",
            "storage_key",
            name="uq_media_files_bucket_storage_key",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("media_files")
    op.drop_index("ix_stories_visibility", table_name="stories")
    op.drop_index("ix_stories_user_id", table_name="stories")
    op.drop_index("ix_stories_status", table_name="stories")
    op.drop_table("stories")
    op.drop_table("users")
