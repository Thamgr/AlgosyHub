from datetime import datetime

from sqlalchemy import DateTime, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import ExternalSource


class Problem(Base):
    __tablename__ = "problems"
    __table_args__ = (UniqueConstraint("external_source", "external_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    external_source: Mapped[ExternalSource]
    external_id: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    difficulty: Mapped[int | None]
    time_limit_ms: Mapped[int | None]
    memory_limit_mb: Mapped[int | None]
    cf_url: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
