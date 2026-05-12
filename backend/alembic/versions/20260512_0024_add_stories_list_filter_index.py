"""Add partial covering index for story list/search base filter.

All public-facing list and search endpoints share the predicate:
    status = 'PUBLISHED' AND visibility = 'PUBLIC' AND deleted_at IS NULL

Individual B-tree indexes on each column exist, but PostgreSQL must bitmap-AND
three separate scans to satisfy this filter.  A single partial index covering
created_at (the default sort column) lets the planner satisfy the full predicate
with one index scan and avoids touching the heap for non-matching rows.

Revision ID: 20260512_0024
Revises: 20260512_0023
Create Date: 2026-05-12 00:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260512_0024"
down_revision: Union[str, Sequence[str], None] = "20260512_0023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Partial covering index: satisfies the base filter for GET /stories,
    # GET /stories/search, GET /stories/timeline, and GET /stories/nearby
    # with a single index scan ordered by created_at DESC.
    op.create_index(
        "ix_stories_published_public_active",
        "stories",
        [sa.text("created_at DESC")],
        unique=False,
        postgresql_where=sa.text("status = 'PUBLISHED' AND visibility = 'PUBLIC' AND deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_stories_published_public_active", table_name="stories")
