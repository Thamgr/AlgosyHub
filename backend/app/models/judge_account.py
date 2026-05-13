from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import ExternalSource


class JudgeAccount(Base):
    """Привязка нашего пользователя к его аккаунту на внешнем judge'е.

    Используется для опроса посылок этого пользователя через публичные API
    (например, ``codeforces.com/api/user.status``) и сопоставления их с
    задачами из наших контестов.
    """

    __tablename__ = "judge_accounts"
    __table_args__ = (UniqueConstraint("user_id", "source"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    source: Mapped[ExternalSource]
    handle: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
