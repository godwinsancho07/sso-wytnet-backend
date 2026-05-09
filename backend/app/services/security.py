"""Security service: IP blocks + account lockout management."""
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blocked_ip import BlockedIP
from app.models.user import User
from app.repositories.audit_log import AuditLogRepository
from app.repositories.user import UserRepository

# Defaults — tune in config later if needed
MAX_FAILED_LOGINS = 5
LOCKOUT_DURATION_MINUTES = 15


class SecurityService:
    def __init__(self, session: AsyncSession):
        self.db = session
        self.audit = AuditLogRepository(session)
        self.users = UserRepository(session)

    # ── IP blocks ───────────────────────────────────────────────────────────

    async def is_ip_blocked(self, ip: Optional[str]) -> bool:
        if not ip:
            return False
        stmt = select(BlockedIP).where(BlockedIP.ip_address == ip)
        result = await self.db.execute(stmt)
        row = result.scalar_one_or_none()
        if not row:
            return False
        if row.expires_at is not None and row.expires_at <= datetime.now(timezone.utc):
            # Expired — auto-clean
            await self.db.delete(row)
            await self.db.flush()
            return False
        return True

    async def block_ip(
        self,
        ip: str,
        reason: Optional[str],
        blocked_by_user_id: Optional[str],
        expires_at: Optional[datetime] = None,
    ) -> BlockedIP:
        # Upsert-ish: if it exists, update reason/expiry
        existing = await self.db.execute(
            select(BlockedIP).where(BlockedIP.ip_address == ip)
        )
        row = existing.scalar_one_or_none()
        if row:
            row.reason = reason
            row.expires_at = expires_at
            row.blocked_by_user_id = blocked_by_user_id
            await self.db.flush()
        else:
            row = BlockedIP(
                ip_address=ip,
                reason=reason,
                blocked_by_user_id=blocked_by_user_id,
                expires_at=expires_at,
            )
            self.db.add(row)
            await self.db.flush()

        await self.audit.log(
            "security.ip_blocked",
            user_id=blocked_by_user_id,
            ip_address=ip,
            metadata={
                "reason": reason,
                "expires_at": expires_at.isoformat() if expires_at else None,
            },
        )
        return row

    async def unblock_ip(self, ip: str, actor_id: Optional[str]) -> bool:
        result = await self.db.execute(
            select(BlockedIP).where(BlockedIP.ip_address == ip)
        )
        row = result.scalar_one_or_none()
        if not row:
            return False
        await self.db.delete(row)
        await self.db.flush()
        await self.audit.log(
            "security.ip_unblocked",
            user_id=actor_id,
            ip_address=ip,
        )
        return True

    async def list_blocked_ips(self) -> List[BlockedIP]:
        result = await self.db.execute(
            select(BlockedIP).order_by(BlockedIP.created_at.desc())
        )
        return list(result.scalars().all())

    # ── Account lockouts ────────────────────────────────────────────────────

    async def record_failed_login(self, user_id: str) -> Optional[User]:
        user = await self.users.get(user_id)
        if not user:
            return None
        user.failed_login_count = (user.failed_login_count or 0) + 1
        if user.failed_login_count >= MAX_FAILED_LOGINS:
            user.locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=LOCKOUT_DURATION_MINUTES
            )
            await self.db.flush()
            await self.audit.log(
                "security.account_locked",
                user_id=user.id,
                metadata={
                    "failed_count": user.failed_login_count,
                    "locked_until": user.locked_until.isoformat(),
                },
            )
        else:
            await self.db.flush()
        return user

    async def reset_failed_logins(self, user_id: str) -> None:
        user = await self.users.get(user_id)
        if not user:
            return
        if user.failed_login_count or user.locked_until:
            user.failed_login_count = 0
            user.locked_until = None
            await self.db.flush()

    @staticmethod
    def is_user_locked(user: User) -> bool:
        if not user or not user.locked_until:
            return False
        return user.locked_until > datetime.now(timezone.utc)

    async def list_locked_or_failing(self) -> List[User]:
        now = datetime.now(timezone.utc)
        stmt = select(User).where(
            (User.failed_login_count > 0) | (User.locked_until > now)
        ).order_by(User.locked_until.desc().nullslast(), User.failed_login_count.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def unlock_user(self, user_id: str, actor_id: Optional[str]) -> Optional[User]:
        user = await self.users.get(user_id)
        if not user:
            return None
        user.failed_login_count = 0
        user.locked_until = None
        await self.db.flush()
        await self.audit.log(
            "security.account_unlocked",
            user_id=user_id,
            metadata={"actor_id": actor_id},
        )
        return user
