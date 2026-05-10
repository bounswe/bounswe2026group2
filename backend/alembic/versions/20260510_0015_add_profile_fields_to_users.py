"""add profile fields to users

Revision ID: 20260510_0015
Revises: 20260508_0014
Create Date: 2026-05-10
"""

import sqlalchemy as sa

from alembic import op

revision = "20260510_0015"
down_revision = "20260508_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("location", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("avatar_bucket_name", sa.String(length=63), nullable=True))
    op.add_column("users", sa.Column("avatar_storage_key", sa.String(length=512), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "avatar_storage_key")
    op.drop_column("users", "avatar_bucket_name")
    op.drop_column("users", "location")
