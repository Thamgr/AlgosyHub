from sqlalchemy import Boolean, CheckConstraint, true
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PlatformSettings(Base):
    __tablename__ = "platform_settings"
    __table_args__ = (CheckConstraint("id = 1", name="platform_settings_singleton"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    registration_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    ai_hints_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
