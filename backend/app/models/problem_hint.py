from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ProblemHint(Base):
    """Three-level AI hints for a problem, cached so we don't re-generate them.

    Hints aren't user-specific (the algorithmic idea is the same for everyone),
    so the row key is just ``problem_id``. ``hint3`` is the full solution; the
    UI gates each level behind an explicit "reveal" click.
    """

    __tablename__ = "problem_hints"

    problem_id: Mapped[int] = mapped_column(
        ForeignKey("problems.id", ondelete="CASCADE"), primary_key=True
    )
    hint1: Mapped[str] = mapped_column(Text, nullable=False)
    hint2: Mapped[str] = mapped_column(Text, nullable=False)
    hint3: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
