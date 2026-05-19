import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from .user import User
    from .oauth_client import OAuthClient

class AppBan(Base):
    __tablename__ = "app_bans"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("oauth_clients.id", ondelete="CASCADE"), nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    banned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    banned_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="bans", foreign_keys=[user_id])
    client: Mapped["OAuthClient"] = relationship("OAuthClient", back_populates="bans")
