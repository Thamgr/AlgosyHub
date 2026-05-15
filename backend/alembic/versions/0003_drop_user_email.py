"""drop users.email — auth теперь по username + password

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-15
"""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Postgres именует inline-`UNIQUE` как `<table>_<column>_key`. Используем
    # IF EXISTS, чтобы миграция не падала на базах, поднятых из более ранней
    # схемы с другим именем констрейнта.
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_email_key")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("email")


def downgrade() -> None:
    # Email мы откатываем как nullable — данных для backfill нет.
    op.add_column(
        "users",
        sa.Column("email", sa.String(255), nullable=True),
    )
    op.create_unique_constraint("users_email_key", "users", ["email"])
