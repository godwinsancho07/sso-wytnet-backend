from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, delete, func

from app.api.deps import CurrentUser, DB
from app.core.exceptions import PermissionDeniedError, AppException
from app.models.client_admin import ClientAdmin
from app.models.oauth_client import OAuthClient
from app.models.user import User
from app.permissions import (
    require_permission, get_owned_client_ids, user_owns_client, is_super_admin,
)
from app.models.token import RefreshToken
from app.repositories.oauth_client import OAuthClientRepository
from app.repositories.user import UserRepository
from app.schemas.oauth import (
    OAuthClientCreate, OAuthClientRead, OAuthClientUpdate, OAuthClientWithSecret,
)
from app.services.client import ClientService
from app.services.integration_docs import render_for_client
from fastapi import status
from fastapi.responses import PlainTextResponse, Response

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("/public", response_model=List[OAuthClientRead])
async def list_public_clients(db: DB) -> List[OAuthClientRead]:
    """Lists all active clients for the public landing page ecosystem."""
    repo = OAuthClientRepository(db)
    clients = await repo.list_active(offset=0, limit=50)
    return [OAuthClientRead.model_validate(c) for c in clients]


@router.post(
    "",
    response_model=OAuthClientWithSecret,
    status_code=201,
    dependencies=[Depends(require_permission("client:create"))],
)
async def create_client(
    body: OAuthClientCreate,
    current_user: CurrentUser,
    db: DB,
) -> OAuthClientWithSecret:
    service = ClientService(db)
    client, secret = await service.create_client(body, actor_id=current_user.id)
    result = OAuthClientRead.model_validate(client).model_dump()
    result["client_secret"] = secret
    return OAuthClientWithSecret(**result)


@router.get(
    "",
    response_model=List[OAuthClientRead],
    dependencies=[Depends(require_permission("client:read"))],
)
async def list_clients(
    current_user: CurrentUser,
    db: DB,
    offset: int = 0,
    limit: int = 50,
) -> List[OAuthClientRead]:
    repo = OAuthClientRepository(db)
    if await is_super_admin(db, current_user):
        clients = await repo.list_active(offset=offset, limit=limit)
    else:
        # App admin: fetch clients via direct JOIN on ClientAdmin — no Python filtering
        stmt = (
            select(OAuthClient)
            .join(ClientAdmin, ClientAdmin.client_id == OAuthClient.id)
            .where(
                ClientAdmin.user_id == current_user.id,
                OAuthClient.is_active == True,
            )
            .order_by(OAuthClient.app_name)
        )
        result = await db.execute(stmt)
        clients = list(result.scalars().all())
    
    results = []
    for c in clients:
        stmt = select(User.email).join(ClientAdmin, ClientAdmin.user_id == User.id).where(ClientAdmin.client_id == c.id)
        emails = (await db.execute(stmt)).scalars().all()
        
        # Calculate unique authorized users
        user_count_stmt = select(func.count(func.distinct(RefreshToken.user_id))).where(RefreshToken.client_id == c.id, RefreshToken.is_revoked == False)
        user_count = (await db.execute(user_count_stmt)).scalar() or 0
        
        # Fetch plan info for limits
        from app.models.plan import Plan
        plan = None
        if c.plan_id:
            plan = await db.get(Plan, c.plan_id)
        
        dto = OAuthClientRead.model_validate(c)
        dto.admin_emails = list(emails)
        dto.user_count = user_count
        dto.credits_used = c.credits_used
        dto.credits_limit = plan.credits_limit if plan else None
        results.append(dto)
    return results


@router.get(
    "/{client_id}",
    response_model=OAuthClientRead,
    dependencies=[Depends(require_permission("client:read"))],
)
async def get_client(
    client_id: str,
    current_user: CurrentUser,
    db: DB,
) -> OAuthClientRead:
    if not await user_owns_client(db, current_user, client_id):
        raise PermissionDeniedError("client:read")
    service = ClientService(db)
    client = await service.get_client(client_id)
    
    stmt = select(User.email).join(ClientAdmin, ClientAdmin.user_id == User.id).where(ClientAdmin.client_id == client.id)
    emails = (await db.execute(stmt)).scalars().all()
    
    dto = OAuthClientRead.model_validate(client)
    dto.admin_emails = list(emails)
    return dto


@router.patch(
    "/{client_id}",
    response_model=OAuthClientRead,
    dependencies=[Depends(require_permission("client:edit"))],
)
async def update_client(
    client_id: str,
    body: OAuthClientUpdate,
    current_user: CurrentUser,
    db: DB,
) -> OAuthClientRead:
    if not await user_owns_client(db, current_user, client_id):
        raise PermissionDeniedError("client:edit")
    service = ClientService(db)
    client = await service.update_client(client_id, body, actor_id=current_user.id)
    return OAuthClientRead.model_validate(client)


@router.delete(
    "/{client_id}",
    status_code=204,
    dependencies=[Depends(require_permission("client:delete"))],
)
async def delete_client(
    client_id: str,
    current_user: CurrentUser,
    db: DB,
) -> None:
    if not await user_owns_client(db, current_user, client_id):
        raise PermissionDeniedError("client:delete")
    service = ClientService(db)
    await service.delete_client(client_id, actor_id=current_user.id)


@router.post(
    "/{client_id}/rotate-secret",
    response_model=OAuthClientWithSecret,
    dependencies=[Depends(require_permission("client:rotate"))],
)
async def rotate_secret(
    client_id: str,
    current_user: CurrentUser,
    db: DB,
) -> OAuthClientWithSecret:
    if not await user_owns_client(db, current_user, client_id):
        raise PermissionDeniedError("client:rotate")
    service = ClientService(db)
    client, secret = await service.rotate_secret(client_id, actor_id=current_user.id)
    
    stmt = select(User.email).join(ClientAdmin, ClientAdmin.user_id == User.id).where(ClientAdmin.client_id == client.id)
    emails = (await db.execute(stmt)).scalars().all()
    
    result = OAuthClientRead.model_validate(client).model_dump()
    result["client_secret"] = secret
    result["admin_emails"] = list(emails)
    return OAuthClientWithSecret(**result)


@router.post(
    "/{client_id}/upgrade-plan",
    response_model=OAuthClientRead,
    dependencies=[Depends(require_permission("client:edit"))],
)
async def upgrade_client_plan(
    client_id: str,
    plan_id: str,
    current_user: CurrentUser,
    db: DB,
) -> OAuthClientRead:
    if not await user_owns_client(db, current_user, client_id):
        raise PermissionDeniedError("client:edit")
    
    from app.models.plan import Plan
    plan = await db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
        
    repo = OAuthClientRepository(db)
    client = await repo.get(client_id)
    
    client.plan_id = plan.id
    client.credits_used = 0 # Reset credits on upgrade
    client.warning_email_sent = False
    
    await db.commit()
    await db.refresh(client)
    return OAuthClientRead.model_validate(client)


# ── Client admin (assignment) management ─────────────────────────────────────

class ClientAdminAssign(BaseModel):
    user_id: str


class ClientAdminRead(BaseModel):
    user_id: str
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    assigned_at: str


@router.get(
    "/{client_id}/admins",
    response_model=List[ClientAdminRead],
    dependencies=[Depends(require_permission("client:read"))],
)
async def list_client_admins(
    client_id: str,
    current_user: CurrentUser,
    db: DB,
) -> List[ClientAdminRead]:
    if not await user_owns_client(db, current_user, client_id):
        raise PermissionDeniedError("client:read")

    stmt = (
        select(ClientAdmin, User)
        .join(User, ClientAdmin.user_id == User.id)
        .where(ClientAdmin.client_id == client_id)
        .order_by(ClientAdmin.assigned_at.desc())
    )
    rows = (await db.execute(stmt)).all()
    return [
        ClientAdminRead(
            user_id=u.id,
            email=u.email,
            full_name=u.full_name,
            avatar_url=u.avatar_url,
            assigned_at=ca.assigned_at.isoformat(),
        )
        for ca, u in rows
    ]


@router.post(
    "/{client_id}/admins",
    response_model=ClientAdminRead,
    status_code=201,
    dependencies=[Depends(require_permission("client:edit"))],
)
async def assign_client_admin(
    client_id: str,
    body: ClientAdminAssign,
    current_user: CurrentUser,
    db: DB,
) -> ClientAdminRead:
    # Only super_admins may grant client admin rights.
    if not await is_super_admin(db, current_user):
        raise PermissionDeniedError("client:edit")

    # Verify client exists
    client_repo = OAuthClientRepository(db)
    client = await client_repo.get(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Verify user exists
    user_repo = UserRepository(db)
    user = await user_repo.get(body.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Idempotent: skip if already assigned
    existing = await db.execute(
        select(ClientAdmin).where(
            ClientAdmin.user_id == body.user_id,
            ClientAdmin.client_id == client_id,
        )
    )
    record = existing.scalar_one_or_none()
    if record is None:
        record = ClientAdmin(user_id=body.user_id, client_id=client_id)
        db.add(record)
        await db.flush()
        await db.refresh(record)
    await db.commit()


    return ClientAdminRead(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        assigned_at=record.assigned_at.isoformat(),
    )


@router.delete(
    "/{client_id}/admins/{user_id}",
    status_code=204,
    dependencies=[Depends(require_permission("client:edit"))],
)
async def remove_client_admin(
    client_id: str,
    user_id: str,
    current_user: CurrentUser,
    db: DB,
) -> None:
    if not await is_super_admin(db, current_user):
        raise PermissionDeniedError("client:edit")
    await db.execute(
        delete(ClientAdmin).where(
            ClientAdmin.user_id == user_id,
            ClientAdmin.client_id == client_id,
        )
    )
    await db.commit()



# ── Integration docs (personalized per client) ───────────────────────────────

@router.get(
    "/{client_id}/integration-docs",
    dependencies=[Depends(require_permission("client:read"))],
    response_class=PlainTextResponse,
)
async def integration_docs_md(
    client_id: str,
    current_user: CurrentUser,
    db: DB,
    download: bool = False,
) -> Response:
    """Returns the integration markdown personalized for this client.

    Use ?download=true to force a file download with a sensible filename.
    Note: client_secret is NEVER embedded here (rotate-secret returns it once).
    """
    if not await user_owns_client(db, current_user, client_id):
        raise PermissionDeniedError("client:read")

    client = await OAuthClientRepository(db).get(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    md = await render_for_client(client)
    headers = {}
    if download:
        safe_name = "".join(c if c.isalnum() else "-" for c in client.app_name).strip("-").lower() or "client"
        headers["Content-Disposition"] = (
            f'attachment; filename="{safe_name}-sso-integration.md"'
        )
    return Response(content=md, media_type="text/markdown", headers=headers)


# ── Self-repair: claim orphaned clients ──────────────────────────────────────

@router.post(
    "/claim-unclaimed",
    dependencies=[Depends(require_permission("client:read"))],
)
async def claim_unclaimed_clients(current_user: CurrentUser, db: DB) -> dict:
    """Auto-assigns the current user as admin for any active clients that have
    NO admin assigned at all (orphaned apps). Safe to call repeatedly — idempotent."""
    from sqlalchemy import not_, exists

    # Find active clients that have zero ClientAdmin rows
    has_admin = exists().where(ClientAdmin.client_id == OAuthClient.id)
    orphan_stmt = (
        select(OAuthClient)
        .where(OAuthClient.is_active == True, ~has_admin)
    )
    result = await db.execute(orphan_stmt)
    orphans = result.scalars().all()

    claimed = []
    for client in orphans:
        db.add(ClientAdmin(user_id=current_user.id, client_id=client.id))
        claimed.append(client.app_name)

    if claimed:
        await db.commit()

    return {"claimed": claimed, "count": len(claimed)}
