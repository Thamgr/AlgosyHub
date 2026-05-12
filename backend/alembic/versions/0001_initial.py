"""initial

Revision ID: 0001
Revises:
Create Date: 2026-05-12
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TYPE userrole AS ENUM ('student', 'teacher')")
    op.execute("CREATE TYPE conteststatus AS ENUM ('draft', 'running', 'finished')")
    op.execute("CREATE TYPE externalsource AS ENUM ('codeforces')")
    op.execute(
        "CREATE TYPE submissionverdict AS ENUM "
        "('pending', 'running', 'accepted', 'wrong_answer', "
        "'time_limit', 'memory_limit', 'runtime_error', 'compilation_error', 'rejected')"
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("username", sa.String(100), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("student", "teacher", name="userrole"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "groups",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("teacher_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.String(1000)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "group_members",
        sa.Column("group_id", sa.Integer, sa.ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    )

    op.create_table(
        "problems",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("external_source", sa.Enum("codeforces", name="externalsource"), nullable=False),
        sa.Column("external_id", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("tags", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("difficulty", sa.Integer),
        sa.Column("time_limit_ms", sa.Integer),
        sa.Column("memory_limit_mb", sa.Integer),
        sa.Column("cf_url", sa.String(500), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("external_source", "external_id"),
    )

    op.create_table(
        "contests",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("group_id", sa.Integer, sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("teacher_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column(
            "status",
            sa.Enum("draft", "running", "finished", name="conteststatus"),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("starts_at", sa.DateTime(timezone=True)),
        sa.Column("ends_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "contest_problems",
        sa.Column("contest_id", sa.Integer, sa.ForeignKey("contests.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("problem_id", sa.Integer, sa.ForeignKey("problems.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("order_index", sa.Integer, nullable=False, server_default="0"),
    )

    op.create_table(
        "submissions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("problem_id", sa.Integer, sa.ForeignKey("problems.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contest_id", sa.Integer, sa.ForeignKey("contests.id", ondelete="SET NULL")),
        sa.Column("language", sa.String(50), nullable=False),
        sa.Column("source_code", sa.Text, nullable=False),
        sa.Column(
            "verdict",
            sa.Enum(
                "pending", "running", "accepted", "wrong_answer",
                "time_limit", "memory_limit", "runtime_error",
                "compilation_error", "rejected",
                name="submissionverdict",
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("external_submission_id", sa.String(100)),
        sa.Column("time_ms", sa.Integer),
        sa.Column("memory_mb", sa.Integer),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "ai_messages",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("problem_id", sa.Integer, sa.ForeignKey("problems.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("ai_messages")
    op.drop_table("submissions")
    op.drop_table("contest_problems")
    op.drop_table("contests")
    op.drop_table("problems")
    op.drop_table("group_members")
    op.drop_table("groups")
    op.drop_table("users")
    op.execute("DROP TYPE submissionverdict")
    op.execute("DROP TYPE externalsource")
    op.execute("DROP TYPE conteststatus")
    op.execute("DROP TYPE userrole")
