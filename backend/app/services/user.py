from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UserNotFoundError
from app.models.user import User
from app.repositories.audit_log import AuditLogRepository
from app.repositories.session import SessionRepository
from app.repositories.social_account import SocialAccountRepository
from app.repositories.token import AccessTokenRepository, RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas.user import UserUpdate


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)
        self.social_accounts = SocialAccountRepository(session)
        self.sessions = SessionRepository(session)
        self.access_tokens = AccessTokenRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)
        self.audit = AuditLogRepository(session)

    async def get_by_id(self, user_id: str) -> User:
        user = await self.users.get(user_id)
        if not user:
            raise UserNotFoundError()
        return user

    async def update_profile(self, user_id: str, data: UserUpdate) -> User:
        user = await self.users.get(user_id)
        if not user:
            raise UserNotFoundError()
        updates = data.model_dump(exclude_none=True)
        if not updates:
            return user
        return await self.users.update(user_id, **updates)

    async def list_users(self, offset: int = 0, limit: int = 50) -> List[User]:
        return await self.users.list(offset=offset, limit=limit)

    async def search_users(self, query: str) -> List[User]:
        return await self.users.search(query)

    async def deactivate(
        self,
        user_id: str,
        actor_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> User:
        # 1. validate
        user = await self.users.get(user_id)
        if not user:
            raise UserNotFoundError()

        # 2. state change
        updated = await self.users.update(user_id, is_active=False)

        # 3. side effects: revoke sessions and tokens
        await self.sessions.revoke_all_for_user(user_id)
        await self.access_tokens.revoke_all_for_user(user_id)
        await self.refresh_tokens.revoke_all_for_user(user_id)

        # 4. audit log
        await self.audit.log(
            event_type="user.suspended",
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"actor_id": actor_id, "target_user_id": user_id},
        )

        # 5. return
        return updated

    async def activate(
        self,
        user_id: str,
        actor_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> User:
        user = await self.users.get(user_id)
        if not user:
            raise UserNotFoundError()

        updated = await self.users.update(user_id, is_active=True)

        await self.audit.log(
            event_type="user.activated",
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"actor_id": actor_id, "target_user_id": user_id},
        )

        return updated

    async def unlink_social_account(self, user_id: str, provider: str) -> None:
        account = await self.social_accounts.get_by_user_and_provider(user_id, provider)
        if account:
            await self.social_accounts.delete(account.id)
