"""Add global display settings for problem topics and difficulty, initially off."""

import sqlalchemy as sa

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("platform_settings", sa.Column("show_problem_tags", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("platform_settings", sa.Column("show_problem_difficulty", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("platform_settings", "show_problem_difficulty")
    op.drop_column("platform_settings", "show_problem_tags")
