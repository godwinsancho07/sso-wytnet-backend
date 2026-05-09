import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class ClientAdmin(Base):
    """Maps a user to an OAuth client they administer (App Admin role scope).

    Industry pattern (Keycloak/Okta): the `app_admin` role gives generic
    capability; this table answers WHICH client(s) a user can administer.
    """
    __tablename__ = "client_admins"
    __table_args__ = (
        UniqueConstraint("user_id", "client_id", name="uq_client_admin"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    client_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("oauth_clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User", backref="administered_clients")
    client = relationship("OAuthClient", backref="admins")
