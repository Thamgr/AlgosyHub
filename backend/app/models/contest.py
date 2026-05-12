from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import ContestStatus

contest_problems = Table(
    "contest_problems",
    Base.metadata,
    Column("contest_id", ForeignKey("contests.id", ondelete="CASCADE"), primary_key=True),
    Column("problem_id", ForeignKey("problems.id", ondelete="CASCADE"), primary_key=True),
    Column("order_index", Integer, nullable=False, default=0),
)


class Contest(Base):
    __tablename__ = "contests"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int | None] = mapped_column(ForeignKey("groups.id", ondelete="SET NULL"))
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[ContestStatus] = mapped_column(default=ContestStatus.draft)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
