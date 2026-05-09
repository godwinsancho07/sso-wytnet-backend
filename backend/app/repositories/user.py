from typing import List, Optional
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email.lower())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_verification_token(self, token: str) -> Optional[User]:
        stmt = select(User).where(User.email_verification_token == token)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_reset_token(self, token: str) -> Optional[User]:
        stmt = select(User).where(User.password_reset_token == token)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_roles(self, user_id: str) -> Optional[User]:
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.user_roles).selectinload("role")
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search(self, query: str, offset: int = 0, limit: int = 50) -> List[User]:
        term = f"%{query}%"
        stmt = (
            select(User)
            .where(or_(User.email.ilike(term), User.full_name.ilike(term)))
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_user(
        self,
        email: str,
        password_hash: Optional[str] = None,
        full_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        email_verified: bool = False,
        email_verification_token: Optional[str] = None,
    ) -> User:
        return await self.create(
            email=email.lower(),
            password_hash=password_hash,
            full_name=full_name,
            avatar_url=avatar_url,
            email_verified=email_verified,
            email_verification_token=email_verification_token,
        )
