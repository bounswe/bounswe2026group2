"""merge heads: view_count + badges

Revision ID: 20260512_0020
Revises: 20260511_0018, 20260510_0019
Create Date: 2026-05-12

"""

from typing import Sequence, Union

revision: str = "20260512_0020"
down_revision: Union[str, Sequence[str], None] = (
    "20260511_0018",
    "20260510_0019",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
