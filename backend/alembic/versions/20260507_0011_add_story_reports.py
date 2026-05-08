"""Add story reports table.

Revision ID: 20260507_0011
Revises: 20260503_0010
Create Date: 2026-05-07 00:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260507_0011"
down_revision: Union[str, Sequence[str], None] = "20260503_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enums
    report_reason_enum = sa.Enum(
        "INAPPROPRIATE_CONTENT", "MISINFORMATION", "OFFENSIVE_LANGUAGE", name="report_reason", native_enum=False
    )
    report_reason_enum.create(op.get_bind(), checkfirst=True)

    report_status_enum = sa.Enum("PENDING", "REVIEWED", "REMOVED", name="report_status", native_enum=False)
    report_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "story_reports",
        sa.Column("story_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "reason",
            sa.Enum(
                "INAPPROPRIATE_CONTENT", "MISINFORMATION", "OFFENSIVE_LANGUAGE", name="report_reason", native_enum=False
            ),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("PENDING", "REVIEWED", "REMOVED", name="report_status", native_enum=False),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("story_id", "user_id", name="uq_story_reports_story_user"),
    )
    op.create_index("ix_story_reports_story_id", "story_reports", ["story_id"], unique=False)
    op.create_index("ix_story_reports_user_id", "story_reports", ["user_id"], unique=False)
    op.create_index("ix_story_reports_status", "story_reports", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_story_reports_status", table_name="story_reports")
    op.drop_index("ix_story_reports_user_id", table_name="story_reports")
    op.drop_index("ix_story_reports_story_id", table_name="story_reports")
    op.drop_table("story_reports")

    # Drop enums
    sa.Enum(
        "INAPPROPRIATE_CONTENT", "MISINFORMATION", "OFFENSIVE_LANGUAGE", name="report_reason", native_enum=False
    ).drop(op.get_bind(), checkfirst=True)
    sa.Enum("PENDING", "REVIEWED", "REMOVED", name="report_status", native_enum=False).drop(
        op.get_bind(), checkfirst=True
    )
