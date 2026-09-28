"""Remove manual contest status without changing schedules or submissions."""

import sqlalchemy as sa

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("contests", "status")


def downgrade() -> None:
    status = sa.Enum("draft", "running", "finished", name="conteststatus")
    status.create(op.get_bind(), checkfirst=True)
    op.add_column("contests", sa.Column("status", status, nullable=False, server_default="running"))
    op.execute("UPDATE contests SET status = 'finished' WHERE ends_at <= CURRENT_TIMESTAMP")
    op.execute("UPDATE contests SET status = 'draft' WHERE starts_at > CURRENT_TIMESTAMP")
