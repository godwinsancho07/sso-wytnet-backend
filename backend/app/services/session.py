from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import SessionInvalidError
from app.models.session import Session
from app.repositories.session import SessionRepository


class SessionService:
    def __init__(self, session: AsyncSession):
        self.sessions = SessionRepository(session)

    async def get_active_sessions(self, user_id: str) -> List[Session]:
        return await self.sessions.list_active_for_user(user_id)

    async def revoke_session(self, session_id: str, user_id: str) -> None:
        session = await self.sessions.get(session_id)
        if not session or session.user_id != user_id:
            raise SessionInvalidError()
        await self.sessions.revoke(session.session_token)

    async def revoke_all_sessions(self, user_id: str) -> int:
        return await self.sessions.revoke_all_for_user(user_id)

    async def validate_session(self, token: str) -> Session:
        session = await self.sessions.get_by_token(token)
        if not session or not session.is_valid:
            raise SessionInvalidError()
        await self.sessions.touch(token)
        return session
