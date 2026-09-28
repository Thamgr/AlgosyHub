from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

contest_problems = Table(
    "contest_problems",
    Base.metadata,
    Column("contest_id", ForeignKey("contests.id", ondelete="CASCADE"), primary_key=True),
    Column("problem_id", ForeignKey("problems.id", ondelete="CASCADE"), primary_key=True),
    Column("order_index", Integer, nullable=False, default=0),
)

# Groups attached to a contest. A user gets access to the contest iff one of
# these groups contains the user (or the user is the contest's teacher).
# Groups here play the role of "tags" — a contest may be exposed to several
# overlapping cohorts at once.
contest_groups = Table(
    "contest_groups",
    Base.metadata,
    Column("contest_id", ForeignKey("contests.id", ondelete="CASCADE"), primary_key=True),
    Column("group_id", ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
)


class Contest(Base):
    __tablename__ = "contests"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int | None] = mapped_column(ForeignKey("groups.id", ondelete="SET NULL"))
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    show_ai_hints: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def has_started(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc)
        return self.starts_at is None or self.starts_at <= now

    def is_active(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc)
        return self.has_started(now) and (self.ends_at is None or now < self.ends_at)
