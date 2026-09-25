"""Global platform settings and explicitly assigned platform administrators."""

from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_platform_admin", sa.Boolean(), nullable=False, server_default=sa.false()))
    table = op.create_table(
        "platform_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("registration_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("ai_hints_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint("id = 1", name="platform_settings_singleton"),
    )
    op.bulk_insert(table, [{"id": 1, "registration_enabled": True, "ai_hints_enabled": True}])


def downgrade() -> None:
    op.drop_table("platform_settings")
    op.drop_column("users", "is_platform_admin")
