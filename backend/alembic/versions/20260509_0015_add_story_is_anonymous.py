"""Add is_anonymous column to stories table.

Revision ID: 20260509_0015
Revises: 20260508_0014
Create Date: 2026-05-09 00:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260509_0015"
down_revision: Union[str, Sequence[str], None] = "20260508_0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "stories",
        sa.Column(
            "is_anonymous",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("stories", "is_anonymous")
