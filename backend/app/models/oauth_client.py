import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Boolean, DateTime, Text, ARRAY
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class OAuthClient(Base):
    __tablename__ = "oauth_clients"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    client_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    client_secret_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    app_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    redirect_uris: Mapped[List[str]] = mapped_column(PG_ARRAY(String(512)), nullable=False, default=list)
    allowed_scopes: Mapped[List[str]] = mapped_column(PG_ARRAY(String(100)), nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_confidential: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    require_pkce: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    authorization_codes: Mapped[List["AuthorizationCode"]] = relationship(
        "AuthorizationCode", back_populates="client", cascade="all, delete-orphan"
    )
    access_tokens: Mapped[List["AccessToken"]] = relationship(
        "AccessToken", back_populates="client", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="client", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<OAuthClient client_id={self.client_id} app_name={self.app_name}>"
