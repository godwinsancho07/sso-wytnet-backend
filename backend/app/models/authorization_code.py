import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class AuthorizationCode(Base):
    __tablename__ = "authorization_codes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    code: Mapped[str] = mapped_column(String(512), unique=True, nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    client_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("oauth_clients.id", ondelete="CASCADE"), nullable=False
    )
    redirect_uri: Mapped[str] = mapped_column(String(512), nullable=False)
    scopes: Mapped[List[str]] = mapped_column(PG_ARRAY(String(100)), nullable=False, default=list)
    code_challenge: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    code_challenge_method: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    nonce: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship("User", back_populates="authorization_codes")
    client: Mapped["OAuthClient"] = relationship("OAuthClient", back_populates="authorization_codes")

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at
