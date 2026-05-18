import uuid
from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Boolean, DateTime, Text, Integer, Float, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
import enum

if TYPE_CHECKING:
    from .oauth_client import OAuthClient
    from .user import User

class PlanType(str, enum.Enum):
    DEVELOPER = "DEVELOPER"
    USER = "USER"

class ResetInterval(str, enum.Enum):
    NEVER = "NEVER"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"

class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[PlanType] = mapped_column(Enum(PlanType), nullable=False, default=PlanType.DEVELOPER)
    price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Limits
    credits_limit: Mapped[int] = mapped_column(Integer, default=0, nullable=False) # 0 for unlimited
    warning_threshold: Mapped[int] = mapped_column(Integer, default=80, nullable=False)
    reset_interval: Mapped[ResetInterval] = mapped_column(Enum(ResetInterval), default=ResetInterval.NEVER, nullable=False)
    app_registrations_limit: Mapped[int] = mapped_column(Integer, default=0, nullable=False) # 0 for unlimited
    
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    oauth_clients: Mapped[List["OAuthClient"]] = relationship("OAuthClient", back_populates="plan")
    users: Mapped[List["User"]] = relationship("User", back_populates="plan")

    def __repr__(self) -> str:
        return f"<Plan name={self.name} type={self.type}>"


class CreditLog(Base):
    __tablename__ = "credit_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # The developer/owner of the app
    owner_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    
    # The app and user involved
    client_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    app_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    target_user_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    event_type: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. "trust_login", "plan_activated"
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    credits_change: Mapped[int] = mapped_column(Integer, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<CreditLog event={self.event_type} app={self.app_name}>"
