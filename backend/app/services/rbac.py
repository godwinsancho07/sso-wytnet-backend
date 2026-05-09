from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PermissionDeniedError, RoleNotFoundError
from app.models.role import Permission, Role
from app.repositories.audit_log import AuditLogRepository
from app.repositories.role import PermissionRepository, RoleRepository


class RBACService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.roles = RoleRepository(session)
        self.permissions = PermissionRepository(session)
        self.audit = AuditLogRepository(session)

    async def create_role(
        self,
        name: str,
        actor_id: str,
        description: str = "",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Role:
        # 2. state change
        role = await self.roles.create(name=name, description=description)

        # 4. audit log
        await self.audit.log(
            event_type="role.created",
            user_id=actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={
                "actor_id": actor_id,
                "role_id": role.id,
                "role_name": role.name,
            },
        )

        return role

    async def get_role(self, role_id: str) -> Role:
        role = await self.roles.get(role_id)
        if not role:
            raise RoleNotFoundError()
        return role

    async def list_roles(self) -> List[Role]:
        return await self.roles.list()

    async def assign_role(
        self,
        user_id: str,
        role_id: str,
        actor_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        # 1. validate
        role = await self.roles.get(role_id)
        if not role:
            raise RoleNotFoundError()

        # 2. state change
        await self.roles.assign_role(user_id, role_id)

        # 4. audit log
        await self.audit.log(
            event_type="role.assigned",
            user_id=actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={
                "actor_id": actor_id,
                "role_id": role_id,
                "role_name": role.name,
                "target_user_id": user_id,
            },
        )

    async def remove_role(
        self,
        user_id: str,
        role_id: str,
        actor_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        # 1. validate (capture role name for audit if available)
        role = await self.roles.get(role_id)
        role_name = role.name if role else None

        # 2. state change
        await self.roles.remove_role(user_id, role_id)

        # 4. audit log
        await self.audit.log(
            event_type="role.removed",
            user_id=actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={
                "actor_id": actor_id,
                "role_id": role_id,
                "role_name": role_name,
                "target_user_id": user_id,
            },
        )

    async def get_user_roles(self, user_id: str) -> List[Role]:
        return await self.roles.get_user_roles(user_id)

    async def get_user_permissions(self, user_id: str) -> List[Permission]:
        return await self.permissions.get_permissions_for_user(user_id)

    async def has_permission(self, user_id: str, permission_name: str) -> bool:
        permissions = await self.get_user_permissions(user_id)
        return any(p.name == permission_name for p in permissions)

    async def require_permission(self, user_id: str, permission_name: str) -> None:
        if not await self.has_permission(user_id, permission_name):
            raise PermissionDeniedError(permission_name)
