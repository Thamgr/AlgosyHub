from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import SubmissionVerdict


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"))
    contest_id: Mapped[int | None] = mapped_column(ForeignKey("contests.id", ondelete="SET NULL"))
    language: Mapped[str] = mapped_column(String(50), nullable=False)
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    verdict: Mapped[SubmissionVerdict] = mapped_column(default=SubmissionVerdict.pending)
    external_submission_id: Mapped[str | None] = mapped_column(String(100))
    time_ms: Mapped[int | None]
    memory_mb: Mapped[int | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
