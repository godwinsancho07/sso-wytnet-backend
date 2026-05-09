"""Admin endpoints for runtime social provider configuration."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DB
from app.core.exceptions import PermissionDeniedError
from app.models.audit_log import AuditLog
from app.permissions import is_super_admin, require_permission
from app.services.provider_settings import (
    SUPPORTED_PROVIDERS,
    ProviderSettingsService,
)

router = APIRouter(prefix="/admin/providers", tags=["admin-providers"])


class ProviderUpdateBody(BaseModel):
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    redirect_uri: Optional[str] = None
    is_enabled: Optional[bool] = None


def _validate_provider(provider: str) -> None:
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown provider: {provider}",
        )


async def _ensure_super_admin(db, current_user) -> None:
    if not await is_super_admin(db, current_user):
        raise PermissionDeniedError("audit:read")


@router.get(
    "",
    dependencies=[Depends(require_permission("audit:read"))],
)
async def list_providers(current_user: CurrentUser, db: DB) -> list:
    await _ensure_super_admin(db, current_user)
    return await ProviderSettingsService(db).list_providers()


@router.patch(
    "/{provider}",
    dependencies=[Depends(require_permission("audit:read"))],
)
async def update_provider(
    provider: str,
    current_user: CurrentUser,
    db: DB,
    body: ProviderUpdateBody = Body(...),
) -> Dict[str, Any]:
    await _ensure_super_admin(db, current_user)
    _validate_provider(provider)
    cfg = await ProviderSettingsService(db).update_provider(
        provider=provider,
        actor_id=current_user.id,
        client_id=body.client_id,
        client_secret=body.client_secret,
        redirect_uri=body.redirect_uri,
        is_enabled=body.is_enabled,
    )
    # Strip secret before returning.
    cfg.pop("client_secret", None)
    return cfg


@router.post(
    "/{provider}/enable",
    dependencies=[Depends(require_permission("audit:read"))],
)
async def enable_provider(
    provider: str, current_user: CurrentUser, db: DB
) -> Dict[str, Any]:
    await _ensure_super_admin(db, current_user)
    _validate_provider(provider)
    cfg = await ProviderSettingsService(db).enable_provider(provider, current_user.id)
    cfg.pop("client_secret", None)
    return cfg


@router.post(
    "/{provider}/disable",
    dependencies=[Depends(require_permission("audit:read"))],
)
async def disable_provider(
    provider: str, current_user: CurrentUser, db: DB
) -> Dict[str, Any]:
    await _ensure_super_admin(db, current_user)
    _validate_provider(provider)
    cfg = await ProviderSettingsService(db).disable_provider(provider, current_user.id)
    cfg.pop("client_secret", None)
    return cfg


@router.get(
    "/{provider}/usage",
    dependencies=[Depends(require_permission("audit:read"))],
)
async def provider_usage(
    provider: str, current_user: CurrentUser, db: DB
) -> Dict[str, Any]:
    """Counts of logins/registrations/links via this provider in the last 30 days."""
    await _ensure_super_admin(db, current_user)
    _validate_provider(provider)

    since = datetime.now(timezone.utc) - timedelta(days=30)

    async def _count(event_type: str) -> int:
        stmt = (
            select(func.count())
            .select_from(AuditLog)
            .where(
                AuditLog.event_type == event_type,
                AuditLog.created_at >= since,
                AuditLog.metadata_["provider"].astext == provider,
            )
        )
        result = await db.execute(stmt)
        return int(result.scalar_one() or 0)

    logins = await _count("auth.social_login")
    registrations = await _count("auth.social_register")
    links = await _count("auth.social_linked")
    failures = await _count("auth.social_failed")

    return {
        "provider": provider,
        "window_days": 30,
        "logins": logins,
        "registrations": registrations,
        "account_links": links,
        "failures": failures,
    }
