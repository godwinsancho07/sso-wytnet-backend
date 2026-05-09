"""CSV export and aggregated reports for admins."""
import csv
import io
import json
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from app.api.deps import DB
from app.models.audit_log import AuditLog
from app.models.token import AccessToken
from app.models.user import User
from app.models.oauth_client import OAuthClient
from app.permissions import require_permission

router = APIRouter(prefix="/reports", tags=["reports"])


def _parse_iso(value: Optional[str], fallback: datetime) -> datetime:
    if not value:
        return fallback
    try:
        # Accept "Z" suffix and bare ISO.
        v = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(v)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid ISO datetime: {value}",
        )


@router.get(
    "/audit.csv",
    dependencies=[Depends(require_permission("audit:read"))],
)
async def export_audit_csv(
    db: DB,
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
) -> StreamingResponse:
    now = datetime.now(timezone.utc)
    start = _parse_iso(from_, now - timedelta(days=30))
    end = _parse_iso(to, now)

    stmt = (
        select(AuditLog)
        .where(AuditLog.created_at >= start, AuditLog.created_at <= end)
        .order_by(AuditLog.created_at.asc())
    )
    if event_type:
        stmt = stmt.where(AuditLog.event_type == event_type)

    result = await db.execute(stmt)
    rows: List[AuditLog] = list(result.scalars().all())

    async def iter_csv() -> AsyncIterator[str]:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "id",
            "created_at",
            "event_type",
            "user_id",
            "ip_address",
            "user_agent",
            "metadata",
        ])
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)

        for log in rows:
            md = ""
            if log.metadata_ is not None:
                try:
                    md = json.dumps(log.metadata_, separators=(",", ":"))
                except (TypeError, ValueError):
                    md = str(log.metadata_)
            writer.writerow([
                log.id,
                log.created_at.isoformat() if log.created_at else "",
                log.event_type or "",
                log.user_id or "",
                log.ip_address or "",
                (log.user_agent or "").replace("\n", " ").replace("\r", " "),
                md,
            ])
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate(0)

    filename = f"audit_{start.date().isoformat()}_{end.date().isoformat()}.csv"
    return StreamingResponse(
        iter_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/login-summary",
    dependencies=[Depends(require_permission("audit:read"))],
)
async def login_summary(db: DB, days: int = Query(30, ge=1, le=365)) -> List[Dict]:
    """By-day buckets: success, failed, social, registrations."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = (
        select(
            func.date_trunc("day", AuditLog.created_at).label("day"),
            AuditLog.event_type,
            func.count().label("count"),
        )
        .where(
            AuditLog.created_at >= since,
            AuditLog.event_type.in_([
                "auth.login",
                "auth.login_failed",
                "auth.social_login",
                "auth.social_register",
                "user.register",
            ]),
        )
        .group_by("day", AuditLog.event_type)
        .order_by("day")
    )
    result = await db.execute(stmt)

    buckets: Dict[str, Dict[str, int]] = {}
    for day, event_type, count in result.all():
        key = day.date().isoformat() if hasattr(day, "date") else str(day)
        b = buckets.setdefault(
            key, {"success": 0, "failed": 0, "social": 0, "registrations": 0}
        )
        if event_type == "auth.login":
            b["success"] += int(count)
        elif event_type == "auth.login_failed":
            b["failed"] += int(count)
        elif event_type in ("auth.social_login", "auth.social_register"):
            b["social"] += int(count)
            if event_type == "auth.social_register":
                b["registrations"] += int(count)
        elif event_type == "user.register":
            b["registrations"] += int(count)

    out = []
    for i in range(days):
        d = (since + timedelta(days=i)).date().isoformat()
        b = buckets.get(d, {"success": 0, "failed": 0, "social": 0, "registrations": 0})
        out.append({"date": d, **b})
    return out


@router.get(
    "/users-growth",
    dependencies=[Depends(require_permission("audit:read"))],
)
async def users_growth(db: DB, days: int = Query(30, ge=1, le=365)) -> List[Dict]:
    """By-day cumulative user count."""
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)

    # Baseline: count of users created strictly before window.
    baseline_stmt = (
        select(func.count()).select_from(User).where(User.created_at < since)
    )
    baseline = int((await db.execute(baseline_stmt)).scalar_one() or 0)

    daily_stmt = (
        select(
            func.date_trunc("day", User.created_at).label("day"),
            func.count().label("count"),
        )
        .where(User.created_at >= since)
        .group_by("day")
        .order_by("day")
    )
    result = await db.execute(daily_stmt)
    by_day: Dict[str, int] = {}
    for day, count in result.all():
        key = day.date().isoformat() if hasattr(day, "date") else str(day)
        by_day[key] = int(count)

    out = []
    cumulative = baseline
    for i in range(days):
        d = (since + timedelta(days=i)).date().isoformat()
        cumulative += by_day.get(d, 0)
        out.append({
            "date": d,
            "new_users": by_day.get(d, 0),
            "total_users": cumulative,
        })
    return out


@router.get(
    "/oauth-usage",
    dependencies=[Depends(require_permission("audit:read"))],
)
async def oauth_usage(db: DB, days: int = Query(30, ge=1, le=365)) -> Dict:
    """Per-client token issuance per day, top 10 clients."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Find top 10 clients by issuance.
    top_stmt = (
        select(
            AccessToken.client_id,
            OAuthClient.app_name,
            OAuthClient.client_id.label("oauth_client_id"),
            func.count().label("count"),
        )
        .join(OAuthClient, AccessToken.client_id == OAuthClient.id)
        .where(AccessToken.created_at >= since)
        .group_by(AccessToken.client_id, OAuthClient.app_name, OAuthClient.client_id)
        .order_by(func.count().desc())
        .limit(10)
    )
    top_result = await db.execute(top_stmt)
    top_rows = top_result.all()
    top_client_ids = [r[0] for r in top_rows]

    daily: List[Dict] = []
    if top_client_ids:
        daily_stmt = (
            select(
                func.date_trunc("day", AccessToken.created_at).label("day"),
                AccessToken.client_id,
                func.count().label("count"),
            )
            .where(
                AccessToken.created_at >= since,
                AccessToken.client_id.in_(top_client_ids),
            )
            .group_by("day", AccessToken.client_id)
            .order_by("day")
        )
        d_res = await db.execute(daily_stmt)
        for day, client_id, count in d_res.all():
            key = day.date().isoformat() if hasattr(day, "date") else str(day)
            daily.append({"date": key, "client_id": client_id, "count": int(count)})

    return {
        "top_clients": [
            {
                "client_db_id": r[0],
                "app_name": r[1],
                "client_id": r[2],
                "tokens": int(r[3]),
            }
            for r in top_rows
        ],
        "daily": daily,
    }


@router.get(
    "/provider-breakdown",
    dependencies=[Depends(require_permission("audit:read"))],
)
async def provider_breakdown(db: DB, days: int = Query(30, ge=1, le=365)) -> List[Dict]:
    """Counts per provider per day from audit_logs metadata->>'provider'."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    provider_expr = AuditLog.metadata_["provider"].astext

    stmt = (
        select(
            func.date_trunc("day", AuditLog.created_at).label("day"),
            provider_expr.label("provider"),
            func.count().label("count"),
        )
        .where(
            AuditLog.created_at >= since,
            AuditLog.event_type.in_([
                "auth.social_login",
                "auth.social_register",
                "auth.social_linked",
            ]),
            provider_expr.isnot(None),
        )
        .group_by("day", "provider")
        .order_by("day")
    )
    result = await db.execute(stmt)
    out: List[Dict] = []
    for day, provider, count in result.all():
        if not provider:
            continue
        key = day.date().isoformat() if hasattr(day, "date") else str(day)
        out.append({"date": key, "provider": provider, "count": int(count)})
    return out
