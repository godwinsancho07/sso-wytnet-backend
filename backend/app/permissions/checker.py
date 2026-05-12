"""
Permission enforcement layer. Industry pattern (AWS IAM / Keycloak):
- Permissions describe CAPABILITY (`client:edit`)
- Ownership/scoping is checked separately, not encoded in permission name
- Super admins bypass ownership checks; app admins must own the resource
"""
from typing import List, Sequence
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DB
from app.core.exceptions import PermissionDeniedError
from app.models import (
    User, Role, Permission, UserRole, RolePermission, ClientAdmin,
)


# ── Permission lookup ─────────────────────────────────────────────────────────

async def get_user_permissions(db: AsyncSession, user: User) -> set[str]:
    """Return the set of permission names a user has via their roles."""
    if user.is_superuser:
        # Superuser bypass: load all permissions defined in the system
        r = await db.execute(select(Permission.name))
        return set(r.scalars().all())

    stmt = (
        select(Permission.name)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id)
        .distinct()
    )
    r = await db.execute(stmt)
    return set(r.scalars().all())


async def get_user_roles(db: AsyncSession, user: User) -> list[str]:
    stmt = (
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id)
    )
    r = await db.execute(stmt)
    return list(r.scalars().all())


# ── Role helpers ──────────────────────────────────────────────────────────────

async def is_super_admin(db: AsyncSession, user: User) -> bool:
    if user.is_superuser:
        return True
    return "super_admin" in await get_user_roles(db, user)


async def is_app_admin(db: AsyncSession, user: User) -> bool:
    return "app_admin" in await get_user_roles(db, user)


# ── Client ownership ──────────────────────────────────────────────────────────

async def user_owns_client(db: AsyncSession, user: User, client_id: str) -> bool:
    """Check if a user is registered as an admin for a specific client."""
    if await is_super_admin(db, user):
        return True
    r = await db.execute(
        select(ClientAdmin).where(
            ClientAdmin.user_id == user.id,
            ClientAdmin.client_id == client_id,
        )
    )
    return r.scalar_one_or_none() is not None


async def get_owned_client_ids(db: AsyncSession, user: User) -> list[str]:
    """Return the set of client IDs (DB primary keys) this user administers."""
    r = await db.execute(
        select(ClientAdmin.client_id).where(ClientAdmin.user_id == user.id)
    )
    return list(r.scalars().all())


# ── PermissionChecker (used in services) ──────────────────────────────────────

class PermissionChecker:
    """Stateful checker for a given user; cached permission set."""
    def __init__(self, db: AsyncSession, user: User):
        self.db = db
        self.user = user
        self._permissions: set[str] | None = None
        self._is_super: bool | None = None

    async def permissions(self) -> set[str]:
        if self._permissions is None:
            self._permissions = await get_user_permissions(self.db, self.user)
        return self._permissions

    async def has(self, permission: str) -> bool:
        return permission in await self.permissions()

    async def has_any(self, permissions: Sequence[str]) -> bool:
        owned = await self.permissions()
        return any(p in owned for p in permissions)

    async def is_super_admin(self) -> bool:
        if self._is_super is None:
            self._is_super = await is_super_admin(self.db, self.user)
        return self._is_super

    async def can_admin_client(self, client_id: str) -> bool:
        return await user_owns_client(self.db, self.user, client_id)


# ── FastAPI dependencies ──────────────────────────────────────────────────────

def require_permission(permission: str):
    """FastAPI dependency factory. Usage:
        @router.post(..., dependencies=[Depends(require_permission("client:create"))])
    """
    async def _dep(user: CurrentUser, db: DB) -> User:
        perms = await get_user_permissions(db, user)
        if not user.is_superuser and permission not in perms:
            raise PermissionDeniedError(permission)
        return user
    return _dep


def require_any_permission(*permissions: str):
    async def _dep(user: CurrentUser, db: DB) -> User:
        owned = await get_user_permissions(db, user)
        if not user.is_superuser and not any(p in owned for p in permissions):
            raise PermissionDeniedError(" or ".join(permissions))
        return user
    return _dep


async def require_super_admin(user: CurrentUser, db: DB) -> User:
    if not await is_super_admin(db, user):
        raise PermissionDeniedError("super_admin")
    return user


def require_client_ownership(client_id_param: str = "client_id"):
    """Path-param-aware dependency: ensures the user can administer the client
    referenced by `{client_id}` (or `{id}`) in the request path."""
    from fastapi import Request

    async def _dep(request: Request, user: CurrentUser, db: DB) -> User:
        cid = request.path_params.get(client_id_param) or request.path_params.get("id")
        if not cid:
            raise PermissionDeniedError("client_ownership")
        if not await user_owns_client(db, user, cid):
            raise PermissionDeniedError("client_ownership")
        return user
    return _dep
