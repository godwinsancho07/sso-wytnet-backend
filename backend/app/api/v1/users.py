from datetime import datetime, timezone, timedelta
from typing import List, Optional
import logging

from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import CurrentUser, DB, get_client_ip
from app.config import settings
from app.core.exceptions import UserNotFoundError
from app.core.security import generate_token
from app.permissions import require_permission
from app.repositories.audit_log import AuditLogRepository
from app.repositories.authorization_code import AuthorizationCodeRepository
from app.repositories.role import RoleRepository
from app.repositories.session import SessionRepository
from app.repositories.social_account import SocialAccountRepository
from app.repositories.token import AccessTokenRepository, RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas.social import SocialAccountRead
from app.schemas.user import UserRead, UserUpdate
from app.services.email import send_password_reset_email
from app.services.user import UserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


# ── Self-scoped endpoints (existing) ────────────────────────────────────────

@router.get("/me", response_model=UserRead)
async def get_profile(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)


@router.patch("/me", response_model=UserRead)
async def update_profile(
    body: UserUpdate,
    current_user: CurrentUser,
    db: DB,
) -> UserRead:
    service = UserService(db)
    user = await service.update_profile(current_user.id, body)
    return UserRead.model_validate(user)


@router.get("/me/social-accounts", response_model=List[SocialAccountRead])
async def list_social_accounts(current_user: CurrentUser, db: DB) -> List[SocialAccountRead]:
    repo = SocialAccountRepository(db)
    accounts = await repo.list_by_user(current_user.id)
    return [SocialAccountRead.model_validate(a) for a in accounts]


@router.delete("/me/social-accounts/{provider}")
async def unlink_social_account(
    provider: str,
    current_user: CurrentUser,
    db: DB,
) -> dict:
    service = UserService(db)
    await service.unlink_social_account(current_user.id, provider)
    return {"unlinked": True}


# ── Admin-scoped user endpoints ─────────────────────────────────────────────

@router.get(
    "",
    dependencies=[Depends(require_permission("user:read"))],
)
async def list_users(
    db: DB,
    q: Optional[str] = Query(None, description="Search query"),
    status: Optional[str] = Query(None, description="active|suspended|unverified"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """Paginated, searchable, filterable user list for admins."""
    user_repo = UserRepository(db)
    role_repo = RoleRepository(db)
    social_repo = SocialAccountRepository(db)
    session_repo = SessionRepository(db)
    auth_code_repo = AuthorizationCodeRepository(db)

    if q:
        users = await user_repo.search(q, offset=offset, limit=limit)
    else:
        users = await user_repo.list(offset=offset, limit=limit)

    if status == "active":
        users = [u for u in users if u.is_active]
    elif status == "suspended":
        users = [u for u in users if not u.is_active]
    elif status == "unverified":
        users = [u for u in users if not u.email_verified]

    items = []
    for u in users:
        roles = await role_repo.get_user_roles(u.id)
        socials = await social_repo.list_by_user(u.id)
        active_sessions = await session_repo.list_active_for_user(u.id)
        connected_apps = await auth_code_repo.count_unique_clients_for_user(u.id)
        items.append({
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "avatar_url": u.avatar_url,
            "email_verified": u.email_verified,
            "is_active": u.is_active,
            "is_superuser": u.is_superuser,
            "created_at": u.created_at.isoformat(),
            "updated_at": u.updated_at.isoformat(),
            "roles": [{"id": r.id, "name": r.name} for r in roles],
            "providers": [s.provider for s in socials],
            "active_sessions": len(active_sessions),
            "connected_apps": connected_apps,
        })

    return {
        "items": items,
        "offset": offset,
        "limit": limit,
        "count": len(items),
    }


@router.get(
    "/{user_id}",
    response_model=UserRead,
    dependencies=[Depends(require_permission("user:read"))],
)
async def get_user(user_id: str, db: DB) -> UserRead:
    service = UserService(db)
    user = await service.get_by_id(user_id)
    return UserRead.model_validate(user)


@router.get(
    "/{user_id}/detail",
    dependencies=[Depends(require_permission("user:read"))],
)
async def get_user_detail(user_id: str, db: DB) -> dict:
    """Aggregate detail for a single user: profile + roles + sessions +
    social accounts + recent audit events."""
    user_repo = UserRepository(db)
    role_repo = RoleRepository(db)
    session_repo = SessionRepository(db)
    social_repo = SocialAccountRepository(db)
    audit_repo = AuditLogRepository(db)

    user = await user_repo.get(user_id)
    if not user:
        raise UserNotFoundError()

    roles = await role_repo.get_user_roles(user_id)
    sessions = await session_repo.list_active_for_user(user_id)
    socials = await social_repo.list_by_user(user_id)
    audit = await audit_repo.list_for_user(user_id, offset=0, limit=20)

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "avatar_url": user.avatar_url,
            "email_verified": user.email_verified,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        },
        "roles": [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "created_at": r.created_at.isoformat(),
            }
            for r in roles
        ],
        "sessions": [
            {
                "id": s.id,
                "device_info": s.device_info,
                "ip_address": s.ip_address,
                "user_agent": s.user_agent,
                "is_revoked": s.is_revoked,
                "expires_at": s.expires_at.isoformat(),
                "last_active_at": s.last_active_at.isoformat(),
                "created_at": s.created_at.isoformat(),
            }
            for s in sessions
        ],
        "social_accounts": [
            {
                "id": sa.id,
                "provider": sa.provider,
                "provider_email": sa.provider_email,
                "created_at": sa.created_at.isoformat(),
            }
            for sa in socials
        ],
        "recent_audit": [
            {
                "id": a.id,
                "event_type": a.event_type,
                "ip_address": a.ip_address,
                "user_agent": a.user_agent,
                "metadata": a.metadata_,
                "created_at": a.created_at.isoformat(),
            }
            for a in audit
        ],
    }


@router.patch(
    "/{user_id}/deactivate",
    response_model=UserRead,
    dependencies=[Depends(require_permission("user:suspend"))],
)
async def deactivate_user(
    user_id: str,
    current_user: CurrentUser,
    request: Request,
    db: DB,
) -> UserRead:
    service = UserService(db)
    user = await service.deactivate(
        user_id,
        actor_id=current_user.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return UserRead.model_validate(user)


@router.patch(
    "/{user_id}/activate",
    response_model=UserRead,
    dependencies=[Depends(require_permission("user:suspend"))],
)
async def activate_user(
    user_id: str,
    current_user: CurrentUser,
    request: Request,
    db: DB,
) -> UserRead:
    service = UserService(db)
    user = await service.activate(
        user_id,
        actor_id=current_user.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return UserRead.model_validate(user)


@router.post(
    "/{user_id}/force-logout",
    dependencies=[Depends(require_permission("user:suspend"))],
)
async def force_logout_user(
    user_id: str,
    current_user: CurrentUser,
    request: Request,
    db: DB,
) -> dict:
    """Revoke all sessions and refresh tokens for the target user."""
    user_repo = UserRepository(db)
    session_repo = SessionRepository(db)
    refresh_repo = RefreshTokenRepository(db)
    access_repo = AccessTokenRepository(db)
    audit_repo = AuditLogRepository(db)

    user = await user_repo.get(user_id)
    if not user:
        raise UserNotFoundError()

    sessions_revoked = await session_repo.revoke_all_for_user(user_id)
    refresh_revoked = await refresh_repo.revoke_all_for_user(user_id)
    access_revoked = await access_repo.revoke_all_for_user(user_id)

    await audit_repo.log(
        event_type="user.force_logout",
        user_id=user_id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        metadata={
            "actor_id": current_user.id,
            "target_user_id": user_id,
            "sessions_revoked": sessions_revoked,
            "refresh_tokens_revoked": refresh_revoked,
            "access_tokens_revoked": access_revoked,
        },
    )

    return {
        "force_logged_out": True,
        "sessions_revoked": sessions_revoked,
        "refresh_tokens_revoked": refresh_revoked,
        "access_tokens_revoked": access_revoked,
    }


@router.post(
    "/{user_id}/admin-reset-password",
    dependencies=[Depends(require_permission("user:suspend"))],
)
async def admin_reset_password(
    user_id: str,
    current_user: CurrentUser,
    request: Request,
    db: DB,
) -> dict:
    """Generate a password reset token for a user and email them the link."""
    user_repo = UserRepository(db)
    audit_repo = AuditLogRepository(db)

    user = await user_repo.get(user_id)
    if not user:
        raise UserNotFoundError()

    reset_token = generate_token(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    await user_repo.update(
        user.id,
        password_reset_token=reset_token,
        password_reset_expires=expires,
    )

    try:
        await send_password_reset_email(user.email, user.full_name, reset_token)
        email_sent = True
    except Exception as e:
        logger.warning(f"admin-reset-password: could not send email to {user.email}: {e}")
        email_sent = False

    await audit_repo.log(
        event_type="user.admin_reset_pw",
        user_id=user_id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        metadata={
            "actor_id": current_user.id,
            "target_user_id": user_id,
            "email_sent": email_sent,
        },
    )

    return {"message": "Reset email sent" if email_sent else "Reset token generated; email send failed"}


@router.delete(
    "/{user_id}",
    dependencies=[Depends(require_permission("user:delete"))],
)
async def delete_user(
    user_id: str,
    current_user: CurrentUser,
    request: Request,
    db: DB,
) -> dict:
    """Hard delete a user. Cascades to sessions, tokens, social accounts, etc."""
    user_repo = UserRepository(db)
    audit_repo = AuditLogRepository(db)

    user = await user_repo.get(user_id)
    if not user:
        raise UserNotFoundError()

    if user.id == current_user.id:
        from app.core.exceptions import AppException
        raise AppException(400, "You cannot delete your own account", "self_delete_forbidden")

    snapshot_email = user.email
    snapshot_name = user.full_name

    # Audit BEFORE delete (audit_log.user_id has ON DELETE SET NULL so we
    # log first while user_id is still meaningful, then delete).
    await audit_repo.log(
        event_type="user.deleted",
        user_id=user_id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        metadata={
            "actor_id": current_user.id,
            "target_user_id": user_id,
            "email": snapshot_email,
            "full_name": snapshot_name,
        },
    )

    await user_repo.delete(user_id)

    return {"deleted": True, "user_id": user_id}
@router.get("/me/connected-apps")
async def get_connected_apps(current_user: CurrentUser, db: DB) -> list:
    """Returns all apps the current user has authorized."""
    from app.models.authorization_code import AuthorizationCode
    from app.models.oauth_client import OAuthClient
    from sqlalchemy import select

    result = await db.execute(
        select(
            OAuthClient.client_id, 
            OAuthClient.app_name, 
            OAuthClient.redirect_uris,
            AuthorizationCode.scopes, 
            AuthorizationCode.created_at
        )
        .join(OAuthClient, OAuthClient.id == AuthorizationCode.client_id)
        .where(AuthorizationCode.user_id == current_user.id)
        .distinct(OAuthClient.client_id)
    )
    rows = result.all()

    return [
        {
            "client_id": row.client_id,
            "app_name": row.app_name,
            "url": row.redirect_uris[0] if row.redirect_uris else "#",
            "scopes": row.scopes or [],
            "last_used": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]
