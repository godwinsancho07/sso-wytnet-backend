from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class NormalizedProfile(BaseModel):
    provider: str
    provider_user_id: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None


class SocialAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    provider: str
    provider_email: Optional[str] = None
    created_at: datetime


class LinkAccountRequest(BaseModel):
    provider: str
    code: str
    state: Optional[str] = None
