"""Add indexes on stories for search and geospatial queries.

Revision ID: 20260424_0009
Revises: 20260419_0007
Create Date: 2026-04-24 00:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260424_0009"
down_revision: Union[str, Sequence[str], None] = "20260419_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Partial composite index for geospatial queries (bounding box + nearby).
    # Only indexes rows that have coordinates, keeping the index small.
    op.create_index(
        "ix_stories_lat_lng",
        "stories",
        ["latitude", "longitude"],
        unique=False,
        postgresql_where=sa.text("latitude IS NOT NULL AND longitude IS NOT NULL"),
    )

    # B-tree index on place_name for equality and prefix lookups.
    # Also speeds up IS NOT NULL checks used in search filters.
    op.create_index("ix_stories_place_name", "stories", ["place_name"], unique=False)

    # Indexes for date-range overlap queries (date_start <= query_end AND date_end >= query_start).
    op.create_index("ix_stories_date_start", "stories", ["date_start"], unique=False)
    op.create_index("ix_stories_date_end", "stories", ["date_end"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_stories_date_end", table_name="stories")
    op.drop_index("ix_stories_date_start", table_name="stories")
    op.drop_index("ix_stories_place_name", table_name="stories")
    op.drop_index("ix_stories_lat_lng", table_name="stories")
