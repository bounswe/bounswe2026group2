"""Add story saves table.

Revision ID: 20260419_0007
Revises: 20260419_0006
Create Date: 2026-04-19 00:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260419_0007"
down_revision: Union[str, Sequence[str], None] = "20260419_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "story_saves",
        sa.Column("story_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("story_id", "user_id", name="uq_story_saves_story_user"),
    )
    op.create_index("ix_story_saves_story_id", "story_saves", ["story_id"], unique=False)
    op.create_index("ix_story_saves_user_id", "story_saves", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_story_saves_user_id", table_name="story_saves")
    op.drop_index("ix_story_saves_story_id", table_name="story_saves")
    op.drop_table("story_saves")
