"""Enable pg_trgm extension and add GIN index on stories.place_name for fuzzy search.

Revision ID: 20260512_0021
Revises: 20260512_0020
Create Date: 2026-05-12 00:00:00
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260512_0021"
down_revision: Union[str, Sequence[str], None] = "20260512_0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_index(
        "ix_stories_place_name_trgm",
        "stories",
        ["place_name"],
        postgresql_using="gin",
        postgresql_ops={"place_name": "gin_trgm_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_stories_place_name_trgm", table_name="stories")
