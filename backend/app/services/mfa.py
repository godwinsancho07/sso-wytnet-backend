"""MFA service: TOTP enrollment + verification + backup codes."""
import secrets
from datetime import datetime, timezone
from typing import List, Optional

import pyotp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User
from app.models.user_mfa import UserMFA
from app.repositories.audit_log import AuditLogRepository
from app.repositories.user import UserRepository

BACKUP_CODE_COUNT = 8
BACKUP_CODE_LEN = 10  # hex chars


def _gen_backup_codes(n: int = BACKUP_CODE_COUNT) -> List[str]:
    return [secrets.token_hex(BACKUP_CODE_LEN // 2) for _ in range(n)]


class MFAService:
    def __init__(self, session: AsyncSession):
        self.db = session
        self.audit = AuditLogRepository(session)
        self.users = UserRepository(session)

    async def _get_row(self, user_id: str) -> Optional[UserMFA]:
        stmt = select(UserMFA).where(UserMFA.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_status(self, user_id: str) -> dict:
        row = await self._get_row(user_id)
        return {
            "is_enabled": bool(row and row.is_enabled),
            "is_required": bool(row and not row.is_enabled and row.totp_secret is None),
            "last_used_at": row.last_used_at.isoformat() if row and row.last_used_at else None,
        }

    async def setup_totp(self, user_id: str) -> dict:
        user = await self.users.get(user_id)
        if not user:
            raise ValueError("user_not_found")

        secret = pyotp.random_base32()
        backup_codes = _gen_backup_codes()
        otpauth_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user.email,
            issuer_name=getattr(settings, "issuer_name", "SSO IdP"),
        )

        row = await self._get_row(user_id)
        if row:
            row.totp_secret = secret
            row.is_enabled = False
            row.backup_codes = backup_codes
        else:
            row = UserMFA(
                user_id=user_id,
                totp_secret=secret,
                is_enabled=False,
                backup_codes=backup_codes,
            )
            self.db.add(row)
        await self.db.flush()

        return {
            "secret": secret,
            "otpauth_uri": otpauth_uri,
            "backup_codes": backup_codes,
        }

    async def confirm_totp(self, user_id: str, code: str) -> bool:
        row = await self._get_row(user_id)
        if not row or not row.totp_secret:
            return False
        if not pyotp.TOTP(row.totp_secret).verify(code, valid_window=1):
            return False
        row.is_enabled = True
        row.last_used_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.audit.log("mfa.enabled", user_id=user_id)
        return True

    async def verify_totp(self, user_id: str, code: str) -> bool:
        row = await self._get_row(user_id)
        if not row or not row.is_enabled or not row.totp_secret:
            return False
        if pyotp.TOTP(row.totp_secret).verify(code, valid_window=1):
            row.last_used_at = datetime.now(timezone.utc)
            await self.db.flush()
            return True
        # Backup code fallback
        if row.backup_codes and code in row.backup_codes:
            remaining = [c for c in row.backup_codes if c != code]
            row.backup_codes = remaining
            row.last_used_at = datetime.now(timezone.utc)
            await self.db.flush()
            await self.audit.log(
                "mfa.backup_code_used",
                user_id=user_id,
                metadata={"remaining": len(remaining)},
            )
            return True
        return False

    async def disable_mfa(self, user_id: str, actor_id: Optional[str]) -> bool:
        row = await self._get_row(user_id)
        if not row:
            return False
        await self.db.delete(row)
        await self.db.flush()
        await self.audit.log(
            "mfa.disabled",
            user_id=user_id,
            metadata={"actor_id": actor_id},
        )
        return True

    async def force_mfa(self, user_id: str, actor_id: Optional[str]) -> UserMFA:
        """Admin marks a user as needing to set up MFA on next login.

        Sentinel: row exists with is_enabled=False and totp_secret=None.
        """
        row = await self._get_row(user_id)
        if row:
            row.is_enabled = False
            row.totp_secret = None
            row.backup_codes = None
        else:
            row = UserMFA(
                user_id=user_id,
                totp_secret=None,
                is_enabled=False,
                backup_codes=None,
            )
            self.db.add(row)
        await self.db.flush()
        await self.audit.log(
            "mfa.required_by_admin",
            user_id=user_id,
            metadata={"actor_id": actor_id},
        )
        return row

    async def is_mfa_enabled_for_user(self, user_id: str) -> bool:
        row = await self._get_row(user_id)
        return bool(row and row.is_enabled)
