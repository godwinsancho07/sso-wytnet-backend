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

    async def search(
        self, 
        query: str, 
        offset: int = 0, 
        limit: int = 50,
        status: Optional[str] = None,
        role: Optional[str] = None
    ) -> List[User]:
        from app.models.role import Role, UserRole
        term = f"%{query}%"
        stmt = select(User).where(or_(User.email.ilike(term), User.full_name.ilike(term)))
        
        if status == "active":
            stmt = stmt.where(User.is_active == True, User.email_verified == True)
        elif status == "suspended":
            stmt = stmt.where(User.is_active == False)
        elif status == "unverified":
            stmt = stmt.where(User.is_active == True, User.email_verified == False)
            
        if role:
            stmt = stmt.join(UserRole, UserRole.user_id == User.id).join(Role, Role.id == UserRole.role_id).where(Role.name == role)

        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_filtered(
        self,
        status: Optional[str] = None,
        role: Optional[str] = None,
        offset: int = 0,
        limit: int = 50
    ) -> List[User]:
        from app.models.role import Role, UserRole
        stmt = select(User)
        
        if status == "active":
            stmt = stmt.where(User.is_active == True, User.email_verified == True)
        elif status == "suspended":
            stmt = stmt.where(User.is_active == False)
        elif status == "unverified":
            stmt = stmt.where(User.is_active == True, User.email_verified == False)
            
        if role:
            stmt = stmt.join(UserRole, UserRole.user_id == User.id).join(Role, Role.id == UserRole.role_id).where(Role.name == role)

        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_filtered(self, query: str = None, status: str = None, role: str = None) -> int:
        from sqlalchemy import func
        from app.models.role import Role, UserRole
        stmt = select(func.count()).select_from(User)
        
        if query:
            term = f"%{query}%"
            stmt = stmt.where(or_(User.email.ilike(term), User.full_name.ilike(term)))
            
        if status == "active":
            stmt = stmt.where(User.is_active == True, User.email_verified == True)
        elif status == "suspended":
            stmt = stmt.where(User.is_active == False)
        elif status == "unverified":
            stmt = stmt.where(User.is_active == True, User.email_verified == False)
            
        if role:
            stmt = stmt.join(UserRole, UserRole.user_id == User.id).join(Role, Role.id == UserRole.role_id).where(Role.name == role)

        result = await self.session.execute(stmt)
        return result.scalar_one() or 0

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

    async def count_connected_apps(self, user_id: str) -> int:
        """Count unique OAuth clients the user has authorized, excluding system apps and apps they own."""
        from app.models.token import RefreshToken
        from app.models.oauth_client import OAuthClient
        from app.models.authorization_code import AuthorizationCode
        from app.models.client_admin import ClientAdmin
        from sqlalchemy import union_all, func

        # 1. Apps with tokens
        stmt1 = (
            select(RefreshToken.client_id)
            .where(RefreshToken.user_id == user_id, RefreshToken.is_revoked == False)
        )
        
        # 2. Apps with codes
        stmt2 = (
            select(AuthorizationCode.client_id)
            .where(AuthorizationCode.user_id == user_id)
        )
        
        combined = union_all(stmt1, stmt2).alias("combined")
        
        # 3. Client IDs where the user is an admin (to exclude them)
        admin_stmt = select(ClientAdmin.client_id).where(ClientAdmin.user_id == user_id)
        
        # Final count of unique clients, excluding 'Internal SSO' and owned apps
        count_stmt = (
            select(func.count(func.distinct(combined.c.client_id)))
            .select_from(combined)
            .join(OAuthClient, OAuthClient.id == combined.c.client_id)
            .where(
                func.lower(OAuthClient.app_name).not_like("%internal sso%"),
                combined.c.client_id.not_in(admin_stmt)
            )
        )
        
        result = await self.session.execute(count_stmt)
        return result.scalar() or 0

    async def count_owned_apps(self, user_id: str) -> int:
        """Count unique OAuth clients the user is an administrator for, excluding Internal SSO."""
        from app.models.client_admin import ClientAdmin
        from app.models.oauth_client import OAuthClient
        from sqlalchemy import func
        
        stmt = (
            select(func.count(ClientAdmin.id))
            .join(OAuthClient, OAuthClient.id == ClientAdmin.client_id)
            .where(
                ClientAdmin.user_id == user_id,
                func.lower(OAuthClient.app_name).not_like("%internal sso%")
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
