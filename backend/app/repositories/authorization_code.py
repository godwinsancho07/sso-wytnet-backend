from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.authorization_code import AuthorizationCode
from app.repositories.base import BaseRepository


class AuthorizationCodeRepository(BaseRepository[AuthorizationCode]):
    def __init__(self, session: AsyncSession):
        super().__init__(AuthorizationCode, session)

    async def get_by_code(self, code: str) -> Optional[AuthorizationCode]:
        stmt = select(AuthorizationCode).where(AuthorizationCode.code == code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def consume(self, code: str) -> Optional[AuthorizationCode]:
        auth_code = await self.get_by_code(code)
        if auth_code and not auth_code.is_used and not auth_code.is_expired:
            await self.update(auth_code.id, is_used=True)
            return auth_code
        return None

    async def count_unique_clients_for_user(self, user_id: str) -> int:
        from sqlalchemy import func
        stmt = (
            select(func.count(AuthorizationCode.client_id.distinct()))
            .where(AuthorizationCode.user_id == user_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
