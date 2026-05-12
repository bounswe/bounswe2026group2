"""Add notifications table.

Revision ID: 20260424_0008
Revises: 20260419_0007
Create Date: 2026-04-24 00:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260424_0008"
down_revision: Union[str, Sequence[str], None] = "20260419_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("recipient_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("story_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("comment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "event_type",
            sa.Enum(
                "story_liked",
                "story_commented",
                "story_bookmarked",
                name="notification_event_type",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["comment_id"], ["story_comments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notifications_recipient_created_at",
        "notifications",
        ["recipient_user_id", "created_at"],
        unique=False,
    )
    op.create_index("ix_notifications_actor_user_id", "notifications", ["actor_user_id"], unique=False)
    op.create_index("ix_notifications_story_id", "notifications", ["story_id"], unique=False)
    op.create_index("ix_notifications_comment_id", "notifications", ["comment_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_notifications_comment_id", table_name="notifications")
    op.drop_index("ix_notifications_story_id", table_name="notifications")
    op.drop_index("ix_notifications_actor_user_id", table_name="notifications")
    op.drop_index("ix_notifications_recipient_created_at", table_name="notifications")
    op.drop_table("notifications")
