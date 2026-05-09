import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class ProviderSetting(Base):
    """Runtime configuration for a social identity provider.

    A row's existence overrides env-var defaults. The client secret is stored
    encrypted at rest (Fernet, key derived from app secret_key).
    """
    __tablename__ = "provider_settings"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    provider: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    client_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    client_secret_encrypted: Mapped[Optional[str]] = mapped_column(
        String(1024), nullable=True
    )
    redirect_uri: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    extra_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    updated_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    updated_by = relationship("User", foreign_keys=[updated_by_user_id])
