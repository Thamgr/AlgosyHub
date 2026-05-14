"""tags (contest↔group M2M) and cached AI problem hints

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-14
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Contest ↔ Group: groups now serve as "tags" attached to a contest.
    # The existing scalar contests.group_id stays for legacy/UI default but
    # access control routes through this M2M table.
    op.create_table(
        "contest_groups",
        sa.Column(
            "contest_id",
            sa.Integer,
            sa.ForeignKey("contests.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "group_id",
            sa.Integer,
            sa.ForeignKey("groups.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    # Backfill the M2M from the legacy single group_id so existing contests
    # remain visible to their group.
    op.execute(
        """
        INSERT INTO contest_groups (contest_id, group_id)
        SELECT id, group_id FROM contests
        WHERE group_id IS NOT NULL
        ON CONFLICT DO NOTHING
        """
    )

    # Cached AI hints per problem — three escalating levels, the third one
    # contains the full solution. Cached per problem (not per user) since
    # hints don't depend on the user.
    op.create_table(
        "problem_hints",
        sa.Column(
            "problem_id",
            sa.Integer,
            sa.ForeignKey("problems.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("hint1", sa.Text, nullable=False),
        sa.Column("hint2", sa.Text, nullable=False),
        sa.Column("hint3", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("problem_hints")
    op.drop_table("contest_groups")
