"""merge heads: google_sub + anon_story + profile_fields

Revision ID: 20260510_0016
Revises: 20260504_0011, 20260509_0015, 20260510_0015
Create Date: 2026-05-10

"""

from typing import Sequence, Union

revision: str = "20260510_0016"
down_revision: Union[str, Sequence[str], None] = (
    "20260504_0011",
    "20260509_0015",
    "20260510_0015",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
