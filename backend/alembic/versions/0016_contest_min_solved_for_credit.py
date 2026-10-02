"""Add an optional minimum solved task count for contest credit."""

import sqlalchemy as sa

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "contests",
        sa.Column(
            "min_solved_for_credit",
            sa.Integer(),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        "ck_contests_min_solved_for_credit_positive",
        "contests",
        "min_solved_for_credit > 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_contests_min_solved_for_credit_positive",
        "contests",
        type_="check",
    )
    op.drop_column("contests", "min_solved_for_credit")
