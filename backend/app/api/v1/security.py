"""Security center: blocked IPs, locked accounts, MFA self-service & admin."""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, DB
from app.core.exceptions import InvalidCredentialsError, UserNotFoundError
from app.core.security import verify_password
from app.permissions import require_permission
from app.repositories.user import UserRepository
from app.services.mfa import MFAService
from app.services.security import SecurityService

router = APIRouter(prefix="", tags=["security"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class BlockIPRequest(BaseModel):
    ip: str = Field(..., min_length=1, max_length=64)
    reason: Optional[str] = None
    expires_at: Optional[datetime] = None


class MFAConfirmRequest(BaseModel):
    code: str = Field(..., min_length=4, max_length=16)


class MFADisableRequest(BaseModel):
    password: str


# ── Admin: blocked IPs ────────────────────────────────────────────────────────

@router.get(
    "/security/blocked-ips",
    dependencies=[Depends(require_permission("audit:read"))],
)
async def list_blocked_ips(db: DB) -> list:
    rows = await SecurityService(db).list_blocked_ips()
    return [
        {
            "id": r.id,
            "ip_address": r.ip_address,
            "reason": r.reason,
            "blocked_by_user_id": r.blocked_by_user_id,
            "created_at": r.created_at.isoformat(),
            "expires_at": r.expires_at.isoformat() if r.expires_at else None,
            "is_expired": r.is_expired,
        }
        for r in rows
    ]


@router.post(
    "/security/blocked-ips",
    dependencies=[Depends(require_permission("audit:read"))],
)
async def block_ip(body: BlockIPRequest, current_user: CurrentUser, db: DB) -> dict:
    row = await SecurityService(db).block_ip(
        ip=body.ip,
        reason=body.reason,
        blocked_by_user_id=current_user.id,
        expires_at=body.expires_at,
    )
    return {
        "id": row.id,
        "ip_address": row.ip_address,
        "reason": row.reason,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
    }


@router.delete(
    "/security/blocked-ips/{ip}",
    dependencies=[Depends(require_permission("audit:read"))],
)
async def unblock_ip(ip: str, current_user: CurrentUser, db: DB) -> dict:
    ok = await SecurityService(db).unblock_ip(ip, current_user.id)
    return {"unblocked": ok}


# ── Admin: locked accounts ────────────────────────────────────────────────────

@router.get(
    "/security/locked-accounts",
    dependencies=[Depends(require_permission("audit:read"))],
)
async def list_locked_accounts(db: DB) -> list:
    users = await SecurityService(db).list_locked_or_failing()
    return [
        {
            "user_id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "failed_login_count": u.failed_login_count,
            "locked_until": u.locked_until.isoformat() if u.locked_until else None,
            "is_locked": SecurityService.is_user_locked(u),
        }
        for u in users
    ]


@router.post(
    "/security/users/{user_id}/unlock",
    dependencies=[Depends(require_permission("audit:read"))],
)
async def unlock_user(user_id: str, current_user: CurrentUser, db: DB) -> dict:
    user = await SecurityService(db).unlock_user(user_id, current_user.id)
    if not user:
        raise UserNotFoundError()
    return {"unlocked": True, "user_id": user.id}


@router.post(
    "/security/users/{user_id}/force-mfa",
    dependencies=[Depends(require_permission("audit:read"))],
)
async def force_mfa(user_id: str, current_user: CurrentUser, db: DB) -> dict:
    user = await UserRepository(db).get(user_id)
    if not user:
        raise UserNotFoundError()
    await MFAService(db).force_mfa(user_id, current_user.id)
    return {"forced": True, "user_id": user_id}


# ── Self-service MFA ──────────────────────────────────────────────────────────

@router.get("/me/mfa/status")
async def my_mfa_status(current_user: CurrentUser, db: DB) -> dict:
    return await MFAService(db).get_status(current_user.id)


@router.get("/me/mfa/setup")
async def my_mfa_setup(current_user: CurrentUser, db: DB) -> dict:
    """Generates a fresh TOTP secret + backup codes (pending confirm)."""
    return await MFAService(db).setup_totp(current_user.id)


@router.post("/me/mfa/confirm")
async def my_mfa_confirm(
    body: MFAConfirmRequest, current_user: CurrentUser, db: DB
) -> dict:
    ok = await MFAService(db).confirm_totp(current_user.id, body.code)
    if not ok:
        raise InvalidCredentialsError()
    return {"is_enabled": True}


@router.post("/me/mfa/disable")
async def my_mfa_disable(
    body: MFADisableRequest, current_user: CurrentUser, db: DB
) -> dict:
    if not current_user.password_hash or not verify_password(
        body.password, current_user.password_hash
    ):
        raise InvalidCredentialsError()
    await MFAService(db).disable_mfa(current_user.id, current_user.id)
    return {"is_enabled": False}
