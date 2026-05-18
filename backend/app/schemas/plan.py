from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from app.models.plan import PlanType, ResetInterval

class PlanBase(BaseModel):
    name: str
    type: PlanType = PlanType.DEVELOPER
    price: float = 0.0
    description: Optional[str] = None
    credits_limit: int = 0
    warning_threshold: int = 80
    reset_interval: ResetInterval = ResetInterval.NEVER
    app_registrations_limit: int = 0
    is_default: bool = False
    is_active: bool = True

class PlanCreate(PlanBase):
    pass

class PlanUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    description: Optional[str] = None
    credits_limit: Optional[int] = None
    warning_threshold: Optional[int] = None
    reset_interval: Optional[ResetInterval] = None
    app_registrations_limit: Optional[int] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None

class PlanResponse(PlanBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PlanStats(BaseModel):
    developer_plans_count: int
    user_plans_count: int
    active_developer_apps_count: int
    total_enrolled_users_count: int
    total_revenue: float
    today_revenue: float
    total_upgrades: int


class CreditLogResponse(BaseModel):
    id: str
    owner_id: str
    client_id: Optional[str]
    app_name: Optional[str]
    target_user_email: Optional[str]
    event_type: str
    description: Optional[str]
    credits_change: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class RazorpayOrderResponse(BaseModel):
    order_id: str
    amount: int
    currency: str
    key_id: str

class RazorpayVerification(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    plan_id: str
    target_client_id: Optional[str] = None
