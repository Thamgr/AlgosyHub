"""contests.show_ai_hints — включать ли блок AI-подсказок

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-30
"""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "contests",
        sa.Column(
            "show_ai_hints",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.alter_column("contests", "show_ai_hints", server_default=None)


def downgrade() -> None:
    op.drop_column("contests", "show_ai_hints")
