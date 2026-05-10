"""Add badges and user_badges tables with initial badge seed data.

Revision ID: 20260510_0019
Revises: 20260510_0018
Create Date: 2026-05-10 00:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260510_0019"
down_revision: Union[str, Sequence[str], None] = "20260510_0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "badges",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("icon_key", sa.String(length=100), nullable=False),
        sa.Column(
            "rule_type",
            sa.Enum(
                "first_story",
                "story_milestone_5",
                "story_milestone_10",
                name="badge_rule_type",
                native_enum=False,
            ),
            nullable=False,
            unique=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_badges_rule_type", "badges", ["rule_type"])

    op.create_table(
        "user_badges",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("badge_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "awarded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["badge_id"], ["badges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "badge_id"),
    )
    op.create_index("ix_user_badges_user_id", "user_badges", ["user_id"])

    # Seed initial badge definitions.
    op.execute(
        """
        INSERT INTO badges (id, name, description, icon_key, rule_type) VALUES
        (gen_random_uuid(), 'First Story',    'Published your very first story.',          'badge_first_story',       'first_story'),
        (gen_random_uuid(), 'Story Teller',   'Published 5 stories on the platform.',      'badge_story_milestone_5', 'story_milestone_5'),
        (gen_random_uuid(), 'Story Master',   'Published 10 stories on the platform.',     'badge_story_milestone_10','story_milestone_10')
        """
    )


def downgrade() -> None:
    op.drop_index("ix_user_badges_user_id", table_name="user_badges")
    op.drop_table("user_badges")
    op.drop_index("ix_badges_rule_type", table_name="badges")
    op.drop_table("badges")
    op.execute("DROP TYPE IF EXISTS badge_rule_type")
