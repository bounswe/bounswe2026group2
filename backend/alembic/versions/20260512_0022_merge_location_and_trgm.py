"""Merge multi-location and pg_trgm branches.

Revision ID: 20260512_0022
Revises: 20260510_0018, 20260512_0021
Create Date: 2026-05-12 00:00:00
"""

from typing import Sequence, Union

revision: str = "20260512_0022"
down_revision: Union[str, Sequence[str], None] = ("20260510_0018", "20260512_0021")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
