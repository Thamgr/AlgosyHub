"""Add an optional emoji avatar to user profiles."""

import sqlalchemy as sa

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("avatar_emoji", sa.String(32), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("users", "avatar_emoji")
