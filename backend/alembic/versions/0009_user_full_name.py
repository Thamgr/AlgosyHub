"""Store the profile name as one field, preserving existing names."""

from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("full_name", sa.String(201), nullable=False, server_default=""))
    op.execute("UPDATE users SET full_name = trim(last_name || ' ' || first_name)")


def downgrade() -> None:
    op.drop_column("users", "full_name")
