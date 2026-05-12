"""Add soft delete fields to stories.

Revision ID: 20260507_0012
Revises: 20260507_0011
Create Date: 2026-05-07 00:30:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260507_0012"
down_revision: Union[str, Sequence[str], None] = "20260507_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("stories", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("stories", sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("stories", sa.Column("delete_reason", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_stories_deleted_by_users",
        "stories",
        "users",
        ["deleted_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_stories_deleted_at", "stories", ["deleted_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_stories_deleted_at", table_name="stories")
    op.drop_constraint("fk_stories_deleted_by_users", "stories", type_="foreignkey")
    op.drop_column("stories", "delete_reason")
    op.drop_column("stories", "deleted_by")
    op.drop_column("stories", "deleted_at")
