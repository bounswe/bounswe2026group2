"""Add story_locations table and backfill from existing story lat/lng.

Revision ID: 20260510_0018
Revises: 20260510_0017
Create Date: 2026-05-10 00:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260510_0018"
down_revision: Union[str, Sequence[str], None] = "20260510_0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "story_locations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("story_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
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
            "latitude >= -90.0 AND latitude <= 90.0",
            name="ck_story_locations_latitude",
        ),
        sa.CheckConstraint(
            "longitude >= -180.0 AND longitude <= 180.0",
            name="ck_story_locations_longitude",
        ),
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_story_locations_story_id", "story_locations", ["story_id"])
    op.create_index("ix_story_locations_coords", "story_locations", ["latitude", "longitude"])

    # Backfill: copy existing primary lat/lng from stories into story_locations as sort_order=0.
    # gen_random_uuid() is available in PostgreSQL 13+ via pgcrypto (enabled by default).
    op.execute(
        """
        INSERT INTO story_locations (id, story_id, latitude, longitude, label, sort_order, created_at, updated_at)
        SELECT gen_random_uuid(), id, latitude, longitude, place_name, 0, now(), now()
        FROM stories
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_story_locations_coords", table_name="story_locations")
    op.drop_index("ix_story_locations_story_id", table_name="story_locations")
    op.drop_table("story_locations")
