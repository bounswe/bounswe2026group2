"""Add user restriction flag.

Revision ID: 20260512_0025
Revises: 20260512_0024
Create Date: 2026-05-12 00:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260512_0025"
down_revision: Union[str, Sequence[str], None] = "20260512_0024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_restricted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("users", "is_restricted")
