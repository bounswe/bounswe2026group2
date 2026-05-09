"""add google_sub to users and make password_hash nullable

Revision ID: 20260504_0011
Revises: 20260503_0010
Create Date: 2026-05-04
"""

import sqlalchemy as sa

from alembic import op

revision = "20260504_0011"
down_revision = "20260503_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("users", "password_hash", nullable=True)
    op.add_column("users", sa.Column("google_sub", sa.String(255), nullable=True))
    op.create_unique_constraint("uq_users_google_sub", "users", ["google_sub"])


def downgrade() -> None:
    op.drop_constraint("uq_users_google_sub", "users", type_="unique")
    op.drop_column("users", "google_sub")
    # password_hash was NOT NULL before this migration, but Google-only users created
    # after upgrade will have password_hash = NULL. Restoring NOT NULL would fail for
    # those rows, so the nullable change is intentionally left in place on downgrade.
