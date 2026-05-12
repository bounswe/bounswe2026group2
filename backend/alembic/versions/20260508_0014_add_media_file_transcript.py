"""Add transcript column to media_files.

Revision ID: 20260508_0014
Revises: 20260508_0013
Create Date: 2026-05-08 00:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260508_0014"
down_revision: Union[str, Sequence[str], None] = "20260508_0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("media_files") as batch_op:
        batch_op.add_column(sa.Column("transcript", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("media_files") as batch_op:
        batch_op.drop_column("transcript")
