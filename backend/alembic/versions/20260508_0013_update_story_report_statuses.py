"""Update story report statuses for moderation workflow.

Revision ID: 20260508_0013
Revises: 20260507_0012
Create Date: 2026-05-08 00:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260508_0013"
down_revision: Union[str, Sequence[str], None] = "20260507_0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


OLD_REPORT_STATUS = sa.Enum("PENDING", "RESOLVED", name="report_status", native_enum=False)
NEW_REPORT_STATUS = sa.Enum("PENDING", "REVIEWED", "REMOVED", name="report_status", native_enum=False)


def upgrade() -> None:
    op.execute("UPDATE story_reports SET status = 'REVIEWED' WHERE status = 'RESOLVED'")

    with op.batch_alter_table("story_reports") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=OLD_REPORT_STATUS,
            type_=NEW_REPORT_STATUS,
            existing_nullable=False,
            server_default="PENDING",
        )


def downgrade() -> None:
    op.execute("UPDATE story_reports SET status = 'RESOLVED' WHERE status IN ('REVIEWED', 'REMOVED')")

    with op.batch_alter_table("story_reports") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=NEW_REPORT_STATUS,
            type_=OLD_REPORT_STATUS,
            existing_nullable=False,
            server_default="PENDING",
        )
