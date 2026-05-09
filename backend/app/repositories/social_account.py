from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.social_account import SocialAccount
from app.repositories.base import BaseRepository


class SocialAccountRepository(BaseRepository[SocialAccount]):
    def __init__(self, session: AsyncSession):
        super().__init__(SocialAccount, session)

    async def get_by_provider(self, provider: str, provider_user_id: str) -> Optional[SocialAccount]:
        stmt = select(SocialAccount).where(
            SocialAccount.provider == provider,
            SocialAccount.provider_user_id == provider_user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_and_provider(self, user_id: str, provider: str) -> Optional[SocialAccount]:
        stmt = select(SocialAccount).where(
            SocialAccount.user_id == user_id,
            SocialAccount.provider == provider,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: str) -> List[SocialAccount]:
        stmt = select(SocialAccount).where(SocialAccount.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def upsert(
        self,
        user_id: str,
        provider: str,
        provider_user_id: str,
        provider_email: Optional[str],
        access_token: Optional[str],
        refresh_token: Optional[str],
    ) -> SocialAccount:
        existing = await self.get_by_provider(provider, provider_user_id)
        if existing:
            return await self.update(
                existing.id,
                provider_email=provider_email,
                access_token=access_token,
                refresh_token=refresh_token,
            )
        return await self.create(
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_email=provider_email,
            access_token=access_token,
            refresh_token=refresh_token,
        )
