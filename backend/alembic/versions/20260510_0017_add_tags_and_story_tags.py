"""Add tags and story_tags tables.

Revision ID: 20260510_0017
Revises: 20260510_0016
Create Date: 2026-05-10 00:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260510_0017"
down_revision: Union[str, Sequence[str], None] = "20260510_0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tags",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_tags_name", "tags", ["name"], unique=False)
    op.create_index("ix_tags_slug", "tags", ["slug"], unique=False)

    op.create_table(
        "story_tags",
        sa.Column("story_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tag_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("story_id", "tag_id"),
    )
    op.create_index("ix_story_tags_story_id", "story_tags", ["story_id"], unique=False)
    op.create_index("ix_story_tags_tag_id", "story_tags", ["tag_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_story_tags_tag_id", table_name="story_tags")
    op.drop_index("ix_story_tags_story_id", table_name="story_tags")
    op.drop_table("story_tags")

    op.drop_index("ix_tags_slug", table_name="tags")
    op.drop_index("ix_tags_name", table_name="tags")
    op.drop_table("tags")
