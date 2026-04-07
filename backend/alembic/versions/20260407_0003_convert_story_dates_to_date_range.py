"""Convert story date fields to DATE range and add precision metadata.

Revision ID: 20260407_0003
Revises: 20260403_0002
Create Date: 2026-04-07 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260407_0003"
down_revision: Union[str, Sequence[str], None] = "20260403_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    date_precision_enum = sa.Enum("year", "date", name="date_precision", native_enum=False)

    op.alter_column(
        "stories",
        "date_start",
        type_=sa.Date(),
        postgresql_using="CASE WHEN date_start IS NULL THEN NULL ELSE make_date(date_start, 1, 1) END",
        existing_nullable=True,
    )
    op.alter_column(
        "stories",
        "date_end",
        type_=sa.Date(),
        postgresql_using="CASE WHEN date_end IS NULL THEN NULL ELSE make_date(date_end, 12, 31) END",
        existing_nullable=True,
    )

    op.add_column(
        "stories",
        sa.Column("date_precision", date_precision_enum, nullable=True),
    )

    op.execute(
        """
        UPDATE stories
        SET date_precision = 'year'
        WHERE date_start IS NOT NULL OR date_end IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_column("stories", "date_precision")

    op.alter_column(
        "stories",
        "date_start",
        type_=sa.Integer(),
        postgresql_using="CASE WHEN date_start IS NULL THEN NULL ELSE EXTRACT(YEAR FROM date_start)::integer END",
        existing_nullable=True,
    )
    op.alter_column(
        "stories",
        "date_end",
        type_=sa.Integer(),
        postgresql_using="CASE WHEN date_end IS NULL THEN NULL ELSE EXTRACT(YEAR FROM date_end)::integer END",
        existing_nullable=True,
    )
