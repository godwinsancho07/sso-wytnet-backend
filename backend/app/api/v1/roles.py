from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DB, get_client_ip
from app.core.exceptions import RoleNotFoundError
from app.models.role import Permission, Role, RolePermission, UserRole
from app.permissions import require_permission
from app.repositories.audit_log import AuditLogRepository
from app.schemas.role import (
    AssignRoleRequest,
    GrantPermissionRequest,
    PermissionRead,
    RemoveRoleRequest,
    RoleCreate,
    RoleDetail,
    RoleRead,
    RoleUpdate,
)
from app.services.rbac import RBACService

router = APIRouter(prefix="/roles", tags=["roles"])

PROTECTED_ROLE_NAMES = {"super_admin", "app_admin", "user"}


@router.post(
    "",
    response_model=RoleRead,
    status_code=201,
    dependencies=[Depends(require_permission("role:create"))],
)
async def create_role(body: RoleCreate, db: DB) -> RoleRead:
    service = RBACService(db)
    role = await service.create_role(body.name, body.description or "")
    return RoleRead.model_validate(role)


@router.get(
    "",
    response_model=List[RoleRead],
    dependencies=[Depends(require_permission("role:read"))],
)
async def list_roles(db: DB) -> List[RoleRead]:
    service = RBACService(db)
    roles = await service.list_roles()
    return [RoleRead.model_validate(r) for r in roles]


@router.post(
    "/assign",
    dependencies=[Depends(require_permission("role:assign"))],
)
async def assign_role(body: AssignRoleRequest, db: DB) -> dict:
    service = RBACService(db)
    await service.assign_role(body.user_id, body.role_id)
    return {"assigned": True}


@router.post(
    "/remove",
    dependencies=[Depends(require_permission("role:assign"))],
)
async def remove_role(body: RemoveRoleRequest, db: DB) -> dict:
    service = RBACService(db)
    await service.remove_role(body.user_id, body.role_id)
    return {"removed": True}


@router.get("/me", response_model=List[RoleRead])
async def my_roles(current_user: CurrentUser, db: DB) -> List[RoleRead]:
    service = RBACService(db)
    roles = await service.get_user_roles(current_user.id)
    return [RoleRead.model_validate(r) for r in roles]


# ── New endpoints ────────────────────────────────────────────────────────────

async def _get_role_or_404(db, role_id: str) -> Role:
    role = await db.get(Role, role_id)
    if not role:
        raise RoleNotFoundError()
    return role


@router.get(
    "/{role_id}",
    response_model=RoleDetail,
    dependencies=[Depends(require_permission("role:read"))],
)
async def get_role(role_id: str, db: DB) -> RoleDetail:
    role = await _get_role_or_404(db, role_id)

    # Permissions for this role
    perm_stmt = (
        select(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role_id)
        .order_by(Permission.resource, Permission.action)
    )
    perms = list((await db.execute(perm_stmt)).scalars().all())

    count_stmt = select(func.count(UserRole.id)).where(UserRole.role_id == role_id)
    user_count = (await db.execute(count_stmt)).scalar_one()

    return RoleDetail(
        id=role.id,
        name=role.name,
        description=role.description,
        created_at=role.created_at,
        permissions=[PermissionRead.model_validate(p) for p in perms],
        user_count=user_count or 0,
        is_protected=role.name in PROTECTED_ROLE_NAMES,
    )


@router.patch(
    "/{role_id}",
    response_model=RoleRead,
    dependencies=[Depends(require_permission("role:create"))],
)
async def update_role(
    role_id: str,
    body: RoleUpdate,
    request: Request,
    current_user: CurrentUser,
    db: DB,
) -> RoleRead:
    role = await _get_role_or_404(db, role_id)

    changes: dict = {}
    if body.name is not None and body.name != role.name:
        if role.name in PROTECTED_ROLE_NAMES and body.name != role.name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot rename protected role '{role.name}'",
            )
        changes["name"] = {"from": role.name, "to": body.name}
        role.name = body.name
    if body.description is not None and body.description != role.description:
        changes["description"] = {"from": role.description, "to": body.description}
        role.description = body.description

    await db.flush()

    audit = AuditLogRepository(db)
    await audit.log(
        event_type="role.updated",
        user_id=current_user.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        metadata={
            "actor_id": current_user.id,
            "role_id": role.id,
            "role_name": role.name,
            "changes": changes,
        },
    )
    await db.commit()
    await db.refresh(role)
    return RoleRead.model_validate(role)


@router.delete(
    "/{role_id}",
    status_code=204,
    dependencies=[Depends(require_permission("role:create"))],
)
async def delete_role(
    role_id: str,
    request: Request,
    current_user: CurrentUser,
    db: DB,
) -> None:
    role = await _get_role_or_404(db, role_id)

    if role.name in PROTECTED_ROLE_NAMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete protected role '{role.name}'",
        )

    role_name = role.name
    await db.delete(role)  # cascade removes user_roles + role_permissions
    await db.flush()

    audit = AuditLogRepository(db)
    await audit.log(
        event_type="role.deleted",
        user_id=current_user.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        metadata={
            "actor_id": current_user.id,
            "role_id": role_id,
            "role_name": role_name,
        },
    )
    await db.commit()


@router.post(
    "/{role_id}/permissions",
    status_code=201,
    dependencies=[Depends(require_permission("role:create"))],
)
async def grant_permission(
    role_id: str,
    body: GrantPermissionRequest,
    request: Request,
    current_user: CurrentUser,
    db: DB,
) -> dict:
    role = await _get_role_or_404(db, role_id)
    permission = await db.get(Permission, body.permission_id)
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")

    existing = await db.execute(
        select(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == body.permission_id,
        )
    )
    if existing.scalar_one_or_none():
        return {"granted": True, "already_granted": True}

    rp = RolePermission(role_id=role_id, permission_id=body.permission_id)
    db.add(rp)
    await db.flush()

    audit = AuditLogRepository(db)
    await audit.log(
        event_type="role.permission_granted",
        user_id=current_user.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        metadata={
            "actor_id": current_user.id,
            "role_id": role.id,
            "role_name": role.name,
            "permission_id": permission.id,
            "permission_name": permission.name,
        },
    )
    await db.commit()
    return {"granted": True}


@router.delete(
    "/{role_id}/permissions/{permission_id}",
    status_code=204,
    dependencies=[Depends(require_permission("role:create"))],
)
async def revoke_permission(
    role_id: str,
    permission_id: str,
    request: Request,
    current_user: CurrentUser,
    db: DB,
) -> None:
    role = await _get_role_or_404(db, role_id)
    permission = await db.get(Permission, permission_id)
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")

    rp_stmt = select(RolePermission).where(
        RolePermission.role_id == role_id,
        RolePermission.permission_id == permission_id,
    )
    rp = (await db.execute(rp_stmt)).scalar_one_or_none()
    if not rp:
        raise HTTPException(status_code=404, detail="Permission not assigned to role")

    await db.delete(rp)
    await db.flush()

    audit = AuditLogRepository(db)
    await audit.log(
        event_type="role.permission_revoked",
        user_id=current_user.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        metadata={
            "actor_id": current_user.id,
            "role_id": role.id,
            "role_name": role.name,
            "permission_id": permission.id,
            "permission_name": permission.name,
        },
    )
    await db.commit()
