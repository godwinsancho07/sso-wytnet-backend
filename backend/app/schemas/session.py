from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    device_info: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_revoked: bool
    expires_at: datetime
    last_active_at: datetime
    created_at: datetime
