from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UserNotFoundError
from app.core.security import hash_password
from app.models.user import User
from app.repositories.audit_log import AuditLogRepository
from app.repositories.session import SessionRepository
from app.repositories.social_account import SocialAccountRepository
from app.repositories.token import AccessTokenRepository, RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserUpdate


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

    async def create_user(
        self,
        data: UserCreate,
        actor_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> User:
        from app.core.exceptions import UserAlreadyExistsError
        
        # Check for existing email
        existing = await self.users.get_by_email(data.email)
        if existing:
            raise UserAlreadyExistsError()

        # Assign default plan
        from app.models.plan import Plan, PlanType
        from sqlalchemy import select
        plan_stmt = select(Plan).where(Plan.type == PlanType.USER, Plan.is_default == True)
        default_plan = (await self.session.execute(plan_stmt)).scalar_one_or_none()
        
        user = await self.users.create_user(
            email=data.email,
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            avatar_url=data.avatar_url,
            email_verified=True,  # Admins create verified users by default
        )
        
        if default_plan:
            user.plan_id = default_plan.id
            await self.session.flush()

        await self.audit.log(
            event_type="user.admin_created",
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"actor_id": actor_id, "email": user.email},
        )

        # Auto-authorize Vote smart AI for new users (if not the admin)
        from app.models.oauth_client import OAuthClient
        from app.models.client_admin import ClientAdmin
        from app.models.token import RefreshToken
        from sqlalchemy import select
        from datetime import datetime, timezone, timedelta

        vote_smart_id = "client_Op_NU6V_ltuKC7OfnL4KGg"
        client_stmt = select(OAuthClient).where(OAuthClient.client_id == vote_smart_id)
        client_res = await self.session.execute(client_stmt)
        vote_client = client_res.scalar_one_or_none()

        if vote_client:
            # Check if this user is an admin of the app (rare for new user but safe)
            admin_stmt = select(ClientAdmin).where(ClientAdmin.user_id == user.id, ClientAdmin.client_id == vote_client.id)
            admin_res = await self.session.execute(admin_stmt)
            if not admin_res.scalar_one_or_none():
                # Auto-authorize: create a long-lived refresh token
                new_token = RefreshToken(
                    user_id=user.id,
                    client_id=vote_client.id,
                    token=f"auto_{user.id[:8]}_{vote_client.id[:8]}",
                    scopes=["openid", "profile", "email"],
                    expires_at=datetime.now(timezone.utc) + timedelta(days=3650), # 10 years
                )
                self.session.add(new_token)
                await self.session.commit()

        return user

    async def update_profile(self, user_id: str, data: UserUpdate) -> User:
        user = await self.users.get(user_id)
        if not user:
            raise UserNotFoundError()
        updates = data.model_dump(exclude_none=True)
        if not updates:
            return user
        return await self.users.update(user_id, **updates)

    async def admin_update_user(
        self,
        user_id: str,
        updates: dict,
        actor_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> User:
        user = await self.users.get(user_id)
        if not user:
            raise UserNotFoundError()

        # Handle password specifically if provided
        if "password" in updates and updates["password"]:
            updates["password_hash"] = hash_password(updates.pop("password"))
        elif "password" in updates:
            updates.pop("password")

        updated = await self.users.update(user_id, **updates)

        await self.audit.log(
            event_type="user.admin_updated",
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"actor_id": actor_id, "target_user_id": user_id, "fields": list(updates.keys())},
        )
        return updated

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
