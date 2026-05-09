from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class PermissionCreate(BaseModel):
    name: str = Field(..., pattern=r"^[a-z_]+:[a-z_]+$")
    description: Optional[str] = None
    resource: str
    action: str


class PermissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    resource: str
    action: str


class PermissionWithUsage(PermissionRead):
    role_count: int = 0


class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    permission_ids: List[str] = []


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime


class RoleDetail(RoleRead):
    permissions: List[PermissionRead] = []
    user_count: int = 0
    is_protected: bool = False


class AssignRoleRequest(BaseModel):
    user_id: str
    role_id: str


class RemoveRoleRequest(BaseModel):
    user_id: str
    role_id: str


class GrantPermissionRequest(BaseModel):
    permission_id: str
