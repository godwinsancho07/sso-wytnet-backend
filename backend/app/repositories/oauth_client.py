from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.oauth_client import OAuthClient
from app.repositories.base import BaseRepository


class OAuthClientRepository(BaseRepository[OAuthClient]):
    def __init__(self, session: AsyncSession):
        super().__init__(OAuthClient, session)

    async def get_by_client_id(self, client_id: str) -> Optional[OAuthClient]:
        stmt = select(OAuthClient).where(
            OAuthClient.client_id == client_id,
            OAuthClient.is_active == True,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active(self, offset: int = 0, limit: int = 100) -> List[OAuthClient]:
        stmt = (
            select(OAuthClient)
            .where(OAuthClient.is_active == True)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
