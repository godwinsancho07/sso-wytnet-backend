from collections import defaultdict
from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DB, get_client_ip
from app.models.role import Permission, RolePermission
from app.permissions import require_permission
from app.repositories.audit_log import AuditLogRepository
from app.schemas.role import PermissionCreate, PermissionRead, PermissionWithUsage

router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.get(
    "",
    response_model=Dict[str, List[PermissionWithUsage]],
    dependencies=[Depends(require_permission("role:read"))],
)
async def list_permissions(db: DB) -> Dict[str, List[PermissionWithUsage]]:
    """List all permissions, grouped by resource."""
    perms_stmt = select(Permission).order_by(Permission.resource, Permission.action)
    perms = list((await db.execute(perms_stmt)).scalars().all())

    # Aggregate role usage per permission
    usage_stmt = (
        select(RolePermission.permission_id, func.count(RolePermission.role_id))
        .group_by(RolePermission.permission_id)
    )
    usage = {pid: count for pid, count in (await db.execute(usage_stmt)).all()}

    grouped: Dict[str, List[PermissionWithUsage]] = defaultdict(list)
    for p in perms:
        grouped[p.resource].append(
            PermissionWithUsage(
                id=p.id,
                name=p.name,
                description=p.description,
                resource=p.resource,
                action=p.action,
                role_count=usage.get(p.id, 0),
            )
        )
    return dict(grouped)


@router.post(
    "",
    response_model=PermissionRead,
    status_code=201,
    dependencies=[Depends(require_permission("role:create"))],
)
async def create_permission(
    body: PermissionCreate,
    request: Request,
    current_user: CurrentUser,
    db: DB,
) -> PermissionRead:
    # Pydantic regex already validates the pattern
    existing = await db.execute(select(Permission).where(Permission.name == body.name))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Permission '{body.name}' already exists",
        )

    permission = Permission(
        name=body.name,
        description=body.description,
        resource=body.resource,
        action=body.action,
    )
    db.add(permission)
    await db.flush()

    audit = AuditLogRepository(db)
    await audit.log(
        event_type="permission.created",
        user_id=current_user.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        metadata={
            "actor_id": current_user.id,
            "permission_id": permission.id,
            "permission_name": permission.name,
            "resource": permission.resource,
            "action": permission.action,
        },
    )
    await db.commit()
    await db.refresh(permission)
    return PermissionRead.model_validate(permission)


@router.delete(
    "/{permission_id}",
    status_code=204,
    dependencies=[Depends(require_permission("role:create"))],
)
async def delete_permission(
    permission_id: str,
    request: Request,
    current_user: CurrentUser,
    db: DB,
) -> None:
    permission = await db.get(Permission, permission_id)
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")

    perm_name = permission.name
    perm_resource = permission.resource
    perm_action = permission.action

    await db.delete(permission)  # cascade removes role_permissions
    await db.flush()

    audit = AuditLogRepository(db)
    await audit.log(
        event_type="permission.deleted",
        user_id=current_user.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        metadata={
            "actor_id": current_user.id,
            "permission_id": permission_id,
            "permission_name": perm_name,
            "resource": perm_resource,
            "action": perm_action,
        },
    )
    await db.commit()
