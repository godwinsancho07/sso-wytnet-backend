from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None


class UserPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    credits_limit: int
    credits_used: int = 0

class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email_verified: bool
    is_active: bool
    is_superuser: bool
    plan_id: Optional[str] = None
    plan: Optional[UserPlanRead] = None
    credits_used: int = 0
    created_at: datetime
    updated_at: datetime


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    email_verified: bool


class UserAdminRead(UserRead):
    social_providers: List[str] = []
    roles: List[str] = []
