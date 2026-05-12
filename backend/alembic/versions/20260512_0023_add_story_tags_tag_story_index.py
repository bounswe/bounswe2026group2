"""Add composite index for tag-based story search.

Revision ID: 20260512_0023
Revises: 20260512_0022
Create Date: 2026-05-12 00:00:00
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260512_0023"
down_revision: Union[str, Sequence[str], None] = "20260512_0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_story_tags_tag_id_story_id",
        "story_tags",
        ["tag_id", "story_id"],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_story_tags_tag_id_story_id", table_name="story_tags")
