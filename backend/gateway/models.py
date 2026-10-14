
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.gateway.database import Base


class Upstream(Base):
    __tablename__ = "upstreams"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
