from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session
from app.repositories.base import BaseRepository


class SessionRepository(BaseRepository[Session]):
    def __init__(self, session: AsyncSession):
        super().__init__(Session, session)

    async def get_by_token(self, token: str) -> Optional[Session]:
        stmt = select(Session).where(Session.session_token == token)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active_for_user(self, user_id: str) -> List[Session]:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        stmt = select(Session).where(
            Session.user_id == user_id,
            Session.is_revoked == False,
            Session.expires_at > now,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def revoke(self, token: str) -> bool:
        stmt = (
            update(Session)
            .where(Session.session_token == token)
            .values(is_revoked=True)
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def revoke_all_for_user(self, user_id: str) -> int:
        stmt = (
            update(Session)
            .where(Session.user_id == user_id, Session.is_revoked == False)
            .values(is_revoked=True)
        )
        result = await self.session.execute(stmt)
        return result.rowcount

    async def touch(self, token: str) -> None:
        from datetime import datetime, timezone
        stmt = (
            update(Session)
            .where(Session.session_token == token)
            .values(last_active_at=datetime.now(timezone.utc))
        )
        await self.session.execute(stmt)
