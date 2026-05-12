"""Operational metrics derived from audit_logs + token + session tables."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    User, OAuthClient, Session, AccessToken, RefreshToken, AuditLog,
)
from app.models.blocked_ip import BlockedIP


class MetricsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def overview(self) -> Dict[str, Any]:
        """KPI cards for super_admin dashboard."""
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        last_24h = now - timedelta(hours=24)

        total_users = await self._count(User)
        active_users = await self._count(User, User.is_active == True)
        total_clients = await self._count(OAuthClient, OAuthClient.is_active == True)

        active_sessions = await self._count(
            Session, Session.is_revoked == False, Session.expires_at > now
        )

        tokens_today = await self._count(
            AccessToken, AccessToken.created_at >= today_start
        )

        failed_logins_24h = await self._count(
            AuditLog,
            AuditLog.event_type == "auth.login_failed",
            AuditLog.created_at >= last_24h,
        )

        successful_logins_24h = await self._count(
            AuditLog,
            AuditLog.event_type == "auth.login",
            AuditLog.created_at >= last_24h,
        )

        social_logins_24h = await self._count(
            AuditLog,
            AuditLog.event_type.in_(["auth.social_login", "auth.social_register"]),
            AuditLog.created_at >= last_24h,
        )

        registrations_24h = await self._count(
            User, User.created_at >= last_24h
        )

        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_clients": total_clients,
            "active_sessions": active_sessions,
            "tokens_today": tokens_today,
            "successful_logins_24h": successful_logins_24h,
            "failed_logins_24h": failed_logins_24h,
            "social_logins_24h": social_logins_24h,
            "registrations_24h": registrations_24h,
            "generated_at": now.isoformat(),
        }

    async def full_overview(self) -> Dict[str, Any]:
        """Complete KPI snapshot for the Super Admin dashboard (all groups)."""
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        last_24h = now - timedelta(hours=24)
        last_1h  = now - timedelta(hours=1)

        # ── User KPIs ────────────────────────────────────────────────────────
        total_users    = await self._count(User)
        active_users   = await self._count(User, User.is_active == True)
        inactive_users = await self._count(User, User.is_active == False)
        blocked_users  = await self._count(
            User, User.is_active == False,
            User.locked_until.isnot(None),
        )
        verified_users   = await self._count(User, User.email_verified == True)
        unverified_users = await self._count(User, User.email_verified == False)

        # ── Auth KPIs ────────────────────────────────────────────────────────
        total_logins_today = await self._count(
            AuditLog,
            AuditLog.event_type == "auth.login",
            AuditLog.created_at >= today_start,
        )
        failed_logins_24h = await self._count(
            AuditLog,
            AuditLog.event_type == "auth.login_failed",
            AuditLog.created_at >= last_24h,
        )
        social_logins_24h = await self._count(
            AuditLog,
            AuditLog.event_type.in_(["auth.social_login", "auth.social_register"]),
            AuditLog.created_at >= last_24h,
        )
        successful_logins_24h = await self._count(
            AuditLog,
            AuditLog.event_type == "auth.login",
            AuditLog.created_at >= last_24h,
        )
        password_logins_24h = max(0, successful_logins_24h - social_logins_24h)
        mfa_logins_24h = await self._count(
            AuditLog,
            AuditLog.event_type == "auth.mfa_verified",
            AuditLog.created_at >= last_24h,
        )
        password_reset_requests_24h = await self._count(
            AuditLog,
            AuditLog.event_type == "auth.password_reset_requested",
            AuditLog.created_at >= last_24h,
        )
        registrations_24h = await self._count(
            User, User.created_at >= last_24h,
        )

        # ── OAuth KPIs ───────────────────────────────────────────────────────
        total_clients    = await self._count(OAuthClient)
        active_clients   = await self._count(OAuthClient, OAuthClient.is_active == True)
        disabled_clients = await self._count(OAuthClient, OAuthClient.is_active == False)

        tokens_today   = await self._count(
            AccessToken, AccessToken.created_at >= today_start
        )
        tokens_revoked = await self._count(
            AccessToken,
            AccessToken.is_revoked == True,
            AccessToken.created_at >= last_24h,
        )
        refresh_active = await self._count(
            RefreshToken,
            RefreshToken.is_revoked == False,
            RefreshToken.expires_at > now,
        )

        # ── Session KPIs ──────────────────────────────────────────────────────
        active_sessions  = await self._count(
            Session, Session.is_revoked == False, Session.expires_at > now
        )
        expired_sessions = await self._count(
            Session, Session.is_revoked == False, Session.expires_at <= now
        )
        revoked_sessions = await self._count(
            Session, Session.is_revoked == True
        )

        # ── Security KPIs ─────────────────────────────────────────────────────
        # Brute-force heuristic: IPs with ≥5 failures in last hour
        suspicious_stmt = (
            select(func.count(func.distinct(AuditLog.ip_address)))
            .where(
                AuditLog.event_type == "auth.login_failed",
                AuditLog.created_at >= last_1h,
                AuditLog.ip_address.isnot(None),
            )
            .having(func.count() >= 5)
        )
        # Use a subquery count approach
        sub = (
            select(AuditLog.ip_address)
            .where(
                AuditLog.event_type == "auth.login_failed",
                AuditLog.created_at >= last_1h,
                AuditLog.ip_address.isnot(None),
            )
            .group_by(AuditLog.ip_address)
            .having(func.count() >= 5)
        ).subquery()
        sus_result = await self.db.execute(
            select(func.count()).select_from(sub)
        )
        suspicious_logins = int(sus_result.scalar_one() or 0)

        blocked_ips = await self._count(BlockedIP, BlockedIP.expires_at > now)
        account_lockouts = await self._count(
            User,
            User.locked_until.isnot(None),
            User.locked_until > now,
        )

        return {
            # Users
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": inactive_users,
            "blocked_users": blocked_users,
            "verified_users": verified_users,
            "unverified_users": unverified_users,
            # Auth
            "total_logins_today": total_logins_today,
            "successful_logins_24h": successful_logins_24h,
            "failed_logins_24h": failed_logins_24h,
            "social_logins_24h": social_logins_24h,
            "password_logins_24h": password_logins_24h,
            "mfa_logins_24h": mfa_logins_24h,
            "password_reset_requests_24h": password_reset_requests_24h,
            "registrations_24h": registrations_24h,
            # OAuth
            "total_clients": total_clients,
            "active_clients": active_clients,
            "disabled_clients": disabled_clients,
            "tokens_today": tokens_today,
            "tokens_revoked_24h": tokens_revoked,
            "refresh_tokens_active": refresh_active,
            # Sessions
            "active_sessions": active_sessions,
            "expired_sessions": expired_sessions,
            "revoked_sessions": revoked_sessions,
            # Security
            "suspicious_logins": suspicious_logins,
            "blocked_ips": blocked_ips,
            "rate_limit_hits_24h": 0,   # Populated by Redis counters if available
            "account_lockouts": account_lockouts,
            "generated_at": now.isoformat(),
        }

    async def login_timeseries(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Hour-by-hour bucketed login counts (success vs failure)."""
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        stmt = (
            select(
                func.date_trunc("hour", AuditLog.created_at).label("hour"),
                AuditLog.event_type,
                func.count().label("count"),
            )
            .where(
                AuditLog.created_at >= since,
                AuditLog.event_type.in_(["auth.login", "auth.login_failed"]),
            )
            .group_by("hour", AuditLog.event_type)
            .order_by("hour")
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        # Pivot
        buckets: Dict[str, Dict[str, int]] = {}
        for hour, event_type, count in rows:
            key = hour.isoformat() if hour else ""
            if key not in buckets:
                buckets[key] = {"hour": key, "success": 0, "failed": 0}
            if event_type == "auth.login":
                buckets[key]["success"] = count
            else:
                buckets[key]["failed"] = count
        return list(buckets.values())

    async def security_alerts(self) -> List[Dict[str, Any]]:
        """Heuristic alerts derived from audit logs."""
        alerts: List[Dict[str, Any]] = []
        last_24h = datetime.now(timezone.utc) - timedelta(hours=24)

        # 1. Failed login spike (>10 in 1h from same IP)
        last_1h = datetime.now(timezone.utc) - timedelta(hours=1)
        stmt = (
            select(AuditLog.ip_address, func.count().label("c"))
            .where(
                AuditLog.event_type == "auth.login_failed",
                AuditLog.created_at >= last_1h,
                AuditLog.ip_address.is_not(None),
            )
            .group_by(AuditLog.ip_address)
            .having(func.count() >= 10)
        )
        result = await self.db.execute(stmt)
        for ip, count in result.all():
            alerts.append({
                "severity": "high",
                "type": "brute_force_suspect",
                "title": f"Failed login spike from {ip}",
                "detail": f"{count} failed attempts in the last hour",
                "ip": ip,
                "count": count,
            })

        # 2. Total failed logins last 24h above threshold
        total_failed = await self._count(
            AuditLog,
            AuditLog.event_type == "auth.login_failed",
            AuditLog.created_at >= last_24h,
        )
        if total_failed > 50:
            alerts.append({
                "severity": "medium",
                "type": "elevated_failures",
                "title": "Elevated failed login volume",
                "detail": f"{total_failed} failed login attempts in last 24h",
                "count": total_failed,
            })

        # 3. Sessions revoked (global logout used) — informational
        revokes = await self._count(
            AuditLog,
            AuditLog.event_type == "auth.global_logout",
            AuditLog.created_at >= last_24h,
        )
        if revokes >= 5:
            alerts.append({
                "severity": "low",
                "type": "global_logout_burst",
                "title": "Multiple global logouts",
                "detail": f"{revokes} users globally logged out in the last 24h",
                "count": revokes,
            })

        return alerts

    async def top_apps(self, limit: int = 5) -> List[Dict[str, Any]]:
        """OAuth clients ranked by recent token issuance."""
        last_7d = datetime.now(timezone.utc) - timedelta(days=7)
        stmt = (
            select(
                OAuthClient.app_name,
                OAuthClient.client_id,
                func.count(AccessToken.id).label("tokens"),
            )
            .join(AccessToken, AccessToken.client_id == OAuthClient.id, isouter=True)
            .where((AccessToken.created_at >= last_7d) | (AccessToken.id.is_(None)))
            .group_by(OAuthClient.id, OAuthClient.app_name, OAuthClient.client_id)
            .order_by(func.count(AccessToken.id).desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return [
            {"app_name": name, "client_id": cid, "tokens_7d": count}
            for name, cid, count in result.all()
        ]

    async def app_overview(self, client_db_id: str) -> Dict[str, Any]:
        """Per-client metrics for App Admin dashboard."""
        now = datetime.now(timezone.utc)
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)

        active_tokens = await self._count(
            AccessToken,
            AccessToken.client_id == client_db_id,
            AccessToken.is_revoked == False,
            AccessToken.expires_at > now,
        )
        tokens_24h = await self._count(
            AccessToken,
            AccessToken.client_id == client_db_id,
            AccessToken.created_at >= last_24h,
        )
        tokens_7d = await self._count(
            AccessToken,
            AccessToken.client_id == client_db_id,
            AccessToken.created_at >= last_7d,
        )

        stmt = (
            select(func.count(func.distinct(RefreshToken.user_id)))
            .where(
                RefreshToken.client_id == client_db_id,
                RefreshToken.is_revoked == False,
            )
        )
        r = await self.db.execute(stmt)
        authorized_users = r.scalar_one() or 0

        active_refresh = await self._count(
            RefreshToken,
            RefreshToken.client_id == client_db_id,
            RefreshToken.is_revoked == False,
            RefreshToken.expires_at > now,
        )

        return {
            "client_id": client_db_id,
            "active_tokens": active_tokens,
            "tokens_24h": tokens_24h,
            "tokens_7d": tokens_7d,
            "authorized_users": authorized_users,
            "active_refresh_tokens": active_refresh,
            "generated_at": now.isoformat(),
        }

    async def app_recent_users(self, client_db_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        stmt = (
            select(
                User.id, User.email, User.full_name, User.avatar_url,
                func.max(AccessToken.created_at).label("last_seen"),
            )
            .join(AccessToken, AccessToken.user_id == User.id)
            .where(AccessToken.client_id == client_db_id)
            .group_by(User.id, User.email, User.full_name, User.avatar_url)
            .order_by(func.max(AccessToken.created_at).desc())
            .limit(limit)
        )
        r = await self.db.execute(stmt)
        return [
            {
                "user_id": uid,
                "email": email,
                "full_name": fn,
                "avatar_url": av,
                "last_seen": ls.isoformat() if ls else None,
            }
            for uid, email, fn, av, ls in r.all()
        ]

    async def user_activity(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        r = await self.db.execute(stmt)
        return [
            {
                "id": log.id,
                "event_type": log.event_type,
                "ip_address": log.ip_address,
                "metadata": log.metadata_,
                "created_at": log.created_at.isoformat(),
            }
            for log in r.scalars().all()
        ]

    async def user_authorized_apps(self, user_id: str) -> List[Dict[str, Any]]:
        stmt = (
            select(
                OAuthClient.id, OAuthClient.client_id, OAuthClient.app_name,
                OAuthClient.logo_url,
                func.max(RefreshToken.created_at).label("authorized_at"),
                func.count(RefreshToken.id).label("token_count"),
            )
            .join(RefreshToken, RefreshToken.client_id == OAuthClient.id)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked == False,
            )
            .group_by(
                OAuthClient.id, OAuthClient.client_id,
                OAuthClient.app_name, OAuthClient.logo_url,
            )
            .order_by(func.max(RefreshToken.created_at).desc())
        )
        r = await self.db.execute(stmt)
        return [
            {
                "id": cid,
                "client_id": client_id,
                "app_name": name,
                "logo_url": logo,
                "authorized_at": auth.isoformat() if auth else None,
                "token_count": tcount,
            }
            for cid, client_id, name, logo, auth, tcount in r.all()
        ]

    async def admin_overview(self, user_id: str) -> Dict[str, Any]:
        """Global metrics for an App Admin (summed over all their owned apps)."""
        from app.models.client_admin import ClientAdmin
        now = datetime.now(timezone.utc)
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)

        # Get owned client IDs
        stmt = select(ClientAdmin.client_id).where(ClientAdmin.user_id == user_id)
        owned_ids = (await self.db.execute(stmt)).scalars().all()
        
        if not owned_ids:
            return {
                "total_apps": 0,
                "total_users": 0,
                "active_tokens": 0,
                "tokens_24h": 0,
                "tokens_7d": 0,
                "generated_at": now.isoformat(),
            }

        total_apps = len(owned_ids)
        
        # Total unique authorized users across all apps
        stmt = (
            select(func.count(func.distinct(RefreshToken.user_id)))
            .where(
                RefreshToken.client_id.in_(owned_ids),
                RefreshToken.is_revoked == False,
            )
        )
        total_users = (await self.db.execute(stmt)).scalar_one() or 0
        
        active_tokens = await self._count(
            AccessToken,
            AccessToken.client_id.in_(owned_ids),
            AccessToken.is_revoked == False,
            AccessToken.expires_at > now,
        )
        
        tokens_24h = await self._count(
            AccessToken,
            AccessToken.client_id.in_(owned_ids),
            AccessToken.created_at >= last_24h,
        )
        
        tokens_7d = await self._count(
            AccessToken,
            AccessToken.client_id.in_(owned_ids),
            AccessToken.created_at >= last_7d,
        )
        
        return {
            "total_apps": total_apps,
            "total_users": total_users,
            "active_tokens": active_tokens,
            "tokens_24h": tokens_24h,
            "tokens_7d": tokens_7d,
            "generated_at": now.isoformat(),
        }

    async def _count(self, model, *filters) -> int:
        stmt = select(func.count()).select_from(model)
        for f in filters:
            stmt = stmt.where(f)
        result = await self.db.execute(stmt)
        return result.scalar_one()
