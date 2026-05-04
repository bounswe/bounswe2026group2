"""Merge notification and search-index heads into a single head.

Revision ID: 20260503_0010
Revises: 20260424_0008, 20260424_0009
Create Date: 2026-05-03
"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "20260503_0010"
down_revision: Union[str, Sequence[str], None] = ("20260424_0008", "20260424_0009")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
