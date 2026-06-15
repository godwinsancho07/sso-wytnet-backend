"""Operational endpoints used by all role dashboards."""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select, update, and_

from app.api.deps import CurrentUser, DB, get_client_ip
from app.core.exceptions import PermissionDeniedError, SessionInvalidError
from app.models.session import Session
from app.models.token import RefreshToken
from app.models.user import User
from app.permissions import (
    require_permission,
    require_super_admin,
    user_owns_client,
    is_super_admin,
)
from app.models.plan import Plan, PlanType, CreditLog
from sqlalchemy import select, update, and_, func
from app.repositories.audit_log import AuditLogRepository
from app.repositories.session import SessionRepository
from app.repositories.user import UserRepository
from app.services.metrics import MetricsService

router = APIRouter(prefix="", tags=["admin"])

@router.get("/plans/revenue")
async def get_revenue_report(
    db: DB,
    current_user: CurrentUser
):
    # Diagnostic: What event types exist?
    types_stmt = select(CreditLog.event_type).distinct()
    found_types = (await db.execute(types_stmt)).scalars().all()
    print(f"DEBUG REVENUE (ADMIN): Found types in DB: {found_types}")
    
    # Total Revenue and count
    # Simplified: Every 'plan_upgrade' log is worth ₹1
    # EXCLUDE specific admin email as requested
    stmt = (
        select(func.count(CreditLog.id))
        .outerjoin(User, CreditLog.owner_id == User.id)
        .where(
            func.lower(CreditLog.event_type) == "plan_upgrade",
            func.coalesce(User.email, "") != "admin@example.com"
        )
    )
    total_payments = (await db.execute(stmt)).scalar() or 0
    print(f"DEBUG REVENUE (ADMIN): Total payments count: {total_payments}")
    total_revenue = float(total_payments) * 1.0
    
    # Recent Payments with User info
    recent_stmt = (
        select(
            CreditLog.created_at, 
            func.coalesce(User.email, "Unknown User"), 
            func.coalesce(Plan.name, "Developer Program Upgrade")
        )
        .outerjoin(User, CreditLog.owner_id == User.id)
        .outerjoin(Plan, User.plan_id == Plan.id)
        .where(
            func.lower(CreditLog.event_type) == "plan_upgrade",
            func.coalesce(User.email, "") != "admin@example.com"
        )
        .order_by(CreditLog.created_at.desc())
        .limit(100)
    )
    recent_results = (await db.execute(recent_stmt)).all()
    
    payments = [
        {
            "date": r[0].isoformat() if r[0] else datetime.now().isoformat(),
            "email": r[1],
            "amount": 1.0,
            "plan_name": r[2]
        }
        for r in recent_results
    ]

    return {
        "total_revenue": total_revenue,
        "total_payments": total_payments,
        "recent_payments": payments,
        "debug": {
            "found_types": found_types,
            "raw_log_count": total_payments
        }
    }


# ── Super Admin metrics ───────────────────────────────────────────────────────

@router.get(
    "/metrics/overview",
    dependencies=[Depends(require_permission("audit:read"))],
)
async def metrics_overview(db: DB) -> dict:
    return await MetricsService(db).overview()


@router.get(
    "/metrics/full-overview",
    dependencies=[Depends(require_permission("audit:read"))],
)
async def metrics_full_overview(db: DB) -> dict:
    """Complete KPI snapshot (all groups) for the Super Admin dashboard."""
    return await MetricsService(db).full_overview()


@router.get(
    "/metrics/login-timeseries",
    dependencies=[Depends(require_permission("audit:read"))],
)
async def metrics_login_timeseries(
    db: DB,
    hours: int = Query(24, ge=1, le=168),
) -> list:
    return await MetricsService(db).login_timeseries(hours)


@router.get(
    "/metrics/top-apps",
    dependencies=[Depends(require_permission("audit:read"))],
)
async def metrics_top_apps(db: DB, limit: int = Query(5, ge=1, le=20)) -> list:
    return await MetricsService(db).top_apps(limit)


@router.get(
    "/security/alerts",
    dependencies=[Depends(require_permission("audit:read"))],
)
async def security_alerts(db: DB) -> list:
    return await MetricsService(db).security_alerts()


@router.get(
    "/audit/recent",
    dependencies=[Depends(require_permission("audit:read"))],
)
async def audit_recent(
    db: DB,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    event_type: Optional[str] = None,
) -> list:
    repo = AuditLogRepository(db)
    if event_type:
        logs = await repo.list_by_event(event_type, offset=offset, limit=limit)
    else:
        logs = await repo.list(offset=offset, limit=limit)
        logs.sort(key=lambda x: x.created_at, reverse=True)
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "event_type": log.event_type,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "metadata": log.metadata_,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]


@router.get("/me/admin/overview")
async def my_admin_overview(current_user: CurrentUser, db: DB) -> dict:
    return await MetricsService(db).admin_overview(current_user.id)


# ── App Admin: per-client metrics ─────────────────────────────────────────────

@router.get("/clients/{client_id}/metrics")
async def app_metrics(client_id: str, current_user: CurrentUser, db: DB) -> dict:
    if not await user_owns_client(db, current_user, client_id):
        raise PermissionDeniedError("client:read")
    return await MetricsService(db).app_overview(client_id)


@router.get("/clients/{client_id}/users")
async def app_users_paginated(
    client_id: str,
    current_user: CurrentUser,
    db: DB,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    q: Optional[str] = Query(None),
) -> dict:
    # Ensure tables exist (temporary fix for missing app_bans)
    from app.db.base import Base
    import app.models
    async with db.bind.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    if not await user_owns_client(db, current_user, client_id):
        raise PermissionDeniedError("client:read")
    return await MetricsService(db).app_users_paginated(client_id, offset, limit, q)


@router.post("/clients/{client_id}/users/{user_id}/ban")
async def ban_user_from_app(
    client_id: str,
    user_id: str,
    current_user: CurrentUser,
    db: DB,
    reason: Optional[str] = None,
) -> dict:
    if not await user_owns_client(db, current_user, client_id):
        raise PermissionDeniedError("client:edit")
    
    from app.models.app_ban import AppBan
    from sqlalchemy import delete
    
    # Check if already banned
    stmt = select(AppBan).where(AppBan.client_id == client_id, AppBan.user_id == user_id)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    
    if not existing:
        ban = AppBan(
            user_id=user_id,
            client_id=client_id,
            reason=reason,
            banned_by=current_user.id
        )
        db.add(ban)
        
        # Revoke all tokens for this user and client to enforce the ban immediately
        from app.models.token import AccessToken, RefreshToken
        from sqlalchemy import update
        
        await db.execute(
            update(AccessToken)
            .where(AccessToken.user_id == user_id, AccessToken.client_id == client_id)
            .values(is_revoked=True)
        )
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.client_id == client_id)
            .values(is_revoked=True)
        )
        
        await db.commit()
    
    return {"status": "banned"}


@router.delete("/clients/{client_id}/users/{user_id}/ban")
async def unban_user_from_app(
    client_id: str,
    user_id: str,
    current_user: CurrentUser,
    db: DB,
) -> dict:
    if not await user_owns_client(db, current_user, client_id):
        raise PermissionDeniedError("client:edit")
    
    from app.models.app_ban import AppBan
    from app.models.token import AccessToken, RefreshToken
    from sqlalchemy import delete, update
    
    await db.execute(
        delete(AppBan).where(AppBan.client_id == client_id, AppBan.user_id == user_id)
    )
    
    # Restore tokens that were revoked by the ban
    await db.execute(
        update(AccessToken)
        .where(AccessToken.user_id == user_id, AccessToken.client_id == client_id)
        .values(is_revoked=False)
    )
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.client_id == client_id)
        .values(is_revoked=False)
    )
    
    await db.commit()
    
    return {"status": "unbanned"}



@router.get("/clients/{client_id}/recent-users")
async def app_recent_users(
    client_id: str,
    current_user: CurrentUser,
    db: DB,
    limit: int = Query(20, ge=1, le=100),
) -> list:
    if not await user_owns_client(db, current_user, client_id):
        raise PermissionDeniedError("client:read")
    return await MetricsService(db).app_recent_users(client_id, limit)


# ── End User: self-scoped ─────────────────────────────────────────────────────

@router.get("/me/activity")
async def my_activity(
    current_user: CurrentUser,
    db: DB,
    limit: int = Query(20, ge=1, le=100),
) -> list:
    return await MetricsService(db).user_activity(current_user.id, limit)


@router.get("/me/authorized-apps")
async def my_authorized_apps(current_user: CurrentUser, db: DB) -> list:
    return await MetricsService(db).user_authorized_apps(current_user.id)


@router.delete("/me/authorized-apps/{client_db_id}")
async def revoke_authorized_app(
    client_db_id: str,
    current_user: CurrentUser,
    db: DB,
) -> dict:
    """Revoke all of the user's tokens for a specific OAuth client."""
    from sqlalchemy import update, delete
    from app.models import AccessToken, RefreshToken, AuthorizationCode

    for model in (AccessToken, RefreshToken):
        await db.execute(
            update(model)
            .where(model.user_id == current_user.id, model.client_id == client_db_id)
            .values(is_revoked=True)
        )
    
    # Also invalidate any pending authorization codes
    await db.execute(
        update(AuthorizationCode)
        .where(AuthorizationCode.user_id == current_user.id, AuthorizationCode.client_id == client_db_id)
        .values(is_used=True)
    )
    
    await db.commit()
    return {"revoked": True}




# ── Super Admin: Sessions across all users ───────────────────────────────────

def _serialize_admin_session(s: Session, user: Optional[User]) -> dict:
    now = datetime.now(timezone.utc)
    expires_at = s.expires_at
    # SQLAlchemy timezone-aware comparison
    is_expired = expires_at <= now if expires_at else False
    if s.is_revoked:
        status_label = "revoked"
    elif is_expired:
        status_label = "expired"
    else:
        status_label = "active"
    return {
        "id": s.id,
        "user_id": s.user_id,
        "user_email": user.email if user else None,
        "user_full_name": user.full_name if user else None,
        "user_avatar_url": user.avatar_url if user else None,
        "device_info": s.device_info,
        "ip_address": s.ip_address,
        "user_agent": s.user_agent,
        "is_revoked": s.is_revoked,
        "is_expired": is_expired,
        "status": status_label,
        "expires_at": s.expires_at.isoformat() if s.expires_at else None,
        "last_active_at": s.last_active_at.isoformat() if s.last_active_at else None,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


@router.get(
    "/admin/sessions",
    dependencies=[Depends(require_super_admin)],
)
async def admin_list_sessions(
    current_user: CurrentUser,
    db: DB,
    user_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List sessions across ALL users — super_admin only."""
    if not await is_super_admin(db, current_user):
        raise PermissionDeniedError("session:read")

    now = datetime.now(timezone.utc)
    stmt = select(Session, User).join(User, Session.user_id == User.id)

    if user_id:
        stmt = stmt.where(Session.user_id == user_id)

    if status_filter == "active":
        stmt = stmt.where(and_(Session.is_revoked == False, Session.expires_at > now))
    elif status_filter == "expired":
        stmt = stmt.where(and_(Session.is_revoked == False, Session.expires_at <= now))
    elif status_filter == "revoked":
        stmt = stmt.where(Session.is_revoked == True)

    stmt = stmt.order_by(Session.last_active_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    rows = result.all()

    return {
        "items": [_serialize_admin_session(s, u) for s, u in rows],
        "offset": offset,
        "limit": limit,
        "count": len(rows),
    }


@router.delete(
    "/admin/sessions/{session_id}",
    status_code=204,
    dependencies=[Depends(require_super_admin)],
)
async def admin_revoke_session(
    session_id: str,
    current_user: CurrentUser,
    db: DB,
    request: Request,
) -> None:
    if not await is_super_admin(db, current_user):
        raise PermissionDeniedError("session:read")

    session_repo = SessionRepository(db)
    target = await session_repo.get(session_id)
    if not target:
        raise SessionInvalidError()

    await session_repo.revoke(target.session_token)

    audit = AuditLogRepository(db)
    await audit.log(
        event_type="session.revoked_by_admin",
        user_id=current_user.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        metadata={
            "session_id": target.id,
            "target_user_id": target.user_id,
            "admin_id": current_user.id,
        },
    )
    await db.commit()



@router.post(
    "/admin/sessions/revoke-user/{user_id}",
    dependencies=[Depends(require_super_admin)],
)
async def admin_revoke_user_sessions(
    user_id: str,
    current_user: CurrentUser,
    db: DB,
    request: Request,
) -> dict:
    """Revoke all sessions and refresh tokens for the target user."""
    if not await is_super_admin(db, current_user):
        raise PermissionDeniedError("session:read")

    user_repo = UserRepository(db)
    target_user = await user_repo.get(user_id)
    if not target_user:
        raise PermissionDeniedError("session:read")

    session_repo = SessionRepository(db)
    revoked_sessions = await session_repo.revoke_all_for_user(user_id)

    rt_result = await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.is_revoked == False)
        .values(is_revoked=True)
    )
    revoked_refresh = rt_result.rowcount or 0

    audit = AuditLogRepository(db)
    await audit.log(
        event_type="session.revoked_by_admin",
        user_id=current_user.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        metadata={
            "scope": "all_user_sessions",
            "target_user_id": user_id,
            "target_user_email": target_user.email,
            "admin_id": current_user.id,
            "sessions_revoked": revoked_sessions,
            "refresh_tokens_revoked": revoked_refresh,
        },
    )
    await db.commit()
    return {
        "revoked_sessions": revoked_sessions,
        "revoked_refresh_tokens": revoked_refresh,

    }
