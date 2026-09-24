"""Add Timus to the shared external source enum."""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE externalsource ADD VALUE IF NOT EXISTS 'timus'")


def downgrade() -> None:
    # PostgreSQL cannot remove an enum label in place. Keep it so that
    # downgrading does not destroy imported problems or linked accounts.
    pass
