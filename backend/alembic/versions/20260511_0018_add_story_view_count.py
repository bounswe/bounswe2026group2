"""Add view_count column to stories table.

Revision ID: 20260511_0018
Revises: 20260510_0017
Create Date: 2026-05-11 00:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260511_0018"
down_revision: Union[str, Sequence[str], None] = "20260510_0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "stories",
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("stories", "view_count")
