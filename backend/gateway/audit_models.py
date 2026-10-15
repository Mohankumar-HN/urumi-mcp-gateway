
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.gateway.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[str] = mapped_column(
        String(100), default="system", nullable=False
    )
    upstream_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    tool_name: Mapped[str] = mapped_column(
        String(200), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    duration_seconds: Mapped[float] = mapped_column(
        Float, nullable=False
    )
    outcome: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
