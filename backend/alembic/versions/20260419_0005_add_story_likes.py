"""Add story likes table.

Revision ID: 20260419_0005
Revises: 20260407_0003
Create Date: 2026-04-19 00:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260419_0005"
down_revision: Union[str, Sequence[str], None] = "20260407_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "story_likes",
        sa.Column("story_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("story_id", "user_id", name="uq_story_likes_story_user"),
    )
    op.create_index("ix_story_likes_story_id", "story_likes", ["story_id"], unique=False)
    op.create_index("ix_story_likes_user_id", "story_likes", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_story_likes_user_id", table_name="story_likes")
    op.drop_index("ix_story_likes_story_id", table_name="story_likes")
    op.drop_table("story_likes")
