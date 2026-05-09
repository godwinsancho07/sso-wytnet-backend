from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.token import AccessToken, RefreshToken
from app.repositories.base import BaseRepository


class AccessTokenRepository(BaseRepository[AccessToken]):
    def __init__(self, session: AsyncSession):
        super().__init__(AccessToken, session)

    async def get_by_token(self, token: str) -> Optional[AccessToken]:
        stmt = select(AccessToken).where(AccessToken.token == token)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(self, token: str) -> bool:
        stmt = (
            update(AccessToken)
            .where(AccessToken.token == token)
            .values(is_revoked=True)
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def revoke_all_for_user(self, user_id: str) -> int:
        stmt = (
            update(AccessToken)
            .where(AccessToken.user_id == user_id, AccessToken.is_revoked == False)
            .values(is_revoked=True)
        )
        result = await self.session.execute(stmt)
        return result.rowcount


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    def __init__(self, session: AsyncSession):
        super().__init__(RefreshToken, session)

    async def get_by_token(self, token: str) -> Optional[RefreshToken]:
        stmt = select(RefreshToken).where(RefreshToken.token == token)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(self, token: str) -> bool:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.token == token)
            .values(is_revoked=True)
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def revoke_all_for_user(self, user_id: str) -> int:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.is_revoked == False)
            .values(is_revoked=True)
        )
        result = await self.session.execute(stmt)
        return result.rowcount

    async def revoke_family(self, parent_token_id: str) -> int:
        """Revoke all tokens in a refresh token rotation family."""
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.parent_token_id == parent_token_id)
            .values(is_revoked=True)
        )
        result = await self.session.execute(stmt)
        return result.rowcount
