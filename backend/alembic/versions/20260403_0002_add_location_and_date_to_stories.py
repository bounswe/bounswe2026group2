"""Add location and date range fields to stories table.

Revision ID: 20260403_0002
Revises: 20260402_0001
Create Date: 2026-04-03 00:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260403_0002"
down_revision: Union[str, Sequence[str], None] = "20260402_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("stories", sa.Column("place_name", sa.String(length=255), nullable=True))
    op.add_column("stories", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("stories", sa.Column("longitude", sa.Float(), nullable=True))
    op.add_column("stories", sa.Column("date_start", sa.Integer(), nullable=True))
    op.add_column("stories", sa.Column("date_end", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_stories_date_range_valid",
        "stories",
        "date_end IS NULL OR date_start IS NULL OR date_end >= date_start",
    )


def downgrade() -> None:
    op.drop_constraint("ck_stories_date_range_valid", "stories", type_="check")
    op.drop_column("stories", "date_end")
    op.drop_column("stories", "date_start")
    op.drop_column("stories", "longitude")
    op.drop_column("stories", "latitude")
    op.drop_column("stories", "place_name")
