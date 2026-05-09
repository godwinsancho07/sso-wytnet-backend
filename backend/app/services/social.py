import logging
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import SocialStateError, UserInactiveError
from app.core.security import generate_token
from app.models.user import User
from app.repositories.social_account import SocialAccountRepository
from app.repositories.user import UserRepository
from app.repositories.audit_log import AuditLogRepository
from app.schemas.social import NormalizedProfile
from app.social.factory import get_provider

logger = logging.getLogger(__name__)

# In-memory state store for OAuth CSRF. In production use Redis.
_state_store: dict[str, str] = {}


class SocialAuthService:
    def __init__(self, session: AsyncSession):
        self.users = UserRepository(session)
        self.social_accounts = SocialAccountRepository(session)
        self.audit = AuditLogRepository(session)

    def build_redirect_url(self, provider_name: str) -> Tuple[str, str]:
        """Return (authorization_url, state) for the given provider."""
        provider = get_provider(provider_name)
        state = generate_token(24)
        _state_store[state] = provider_name
        return provider.get_authorization_url(state), state

    async def handle_callback(
        self,
        provider_name: str,
        code: str,
        state: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> User:
        # Validate state
        if _state_store.pop(state, None) != provider_name:
            raise SocialStateError()

        provider = get_provider(provider_name)
        profile, _ = await provider.fetch_normalized_profile(code)

        return await self._resolve_user(profile, ip_address, user_agent)

    async def _resolve_user(
        self,
        profile: NormalizedProfile,
        ip_address: Optional[str],
        user_agent: Optional[str],
    ) -> User:
        # 1. Check if this social account already exists → get user
        existing_social = await self.social_accounts.get_by_provider(
            profile.provider, profile.provider_user_id
        )
        if existing_social:
            user = await self.users.get(existing_social.user_id)
            if not user or not user.is_active:
                raise UserInactiveError()
            await self.social_accounts.upsert(
                user_id=user.id,
                provider=profile.provider,
                provider_user_id=profile.provider_user_id,
                provider_email=profile.email,
                access_token=profile.access_token,
                refresh_token=profile.refresh_token,
            )
            await self.audit.log(
                "auth.social_login",
                user_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"provider": profile.provider},
            )
            return user

        # 2. Try to link by email
        if profile.email:
            user = await self.users.get_by_email(profile.email)
            if user:
                if not user.is_active:
                    raise UserInactiveError()
                await self.social_accounts.upsert(
                    user_id=user.id,
                    provider=profile.provider,
                    provider_user_id=profile.provider_user_id,
                    provider_email=profile.email,
                    access_token=profile.access_token,
                    refresh_token=profile.refresh_token,
                )
                await self.audit.log(
                    "auth.social_link",
                    user_id=user.id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    metadata={"provider": profile.provider},
                )
                return user

        # 3. Create a new user
        user = await self.users.create_user(
            email=profile.email or f"{profile.provider}_{profile.provider_user_id}@sso.local",
            full_name=profile.full_name,
            avatar_url=profile.avatar_url,
            email_verified=bool(profile.email),
        )
        await self.social_accounts.upsert(
            user_id=user.id,
            provider=profile.provider,
            provider_user_id=profile.provider_user_id,
            provider_email=profile.email,
            access_token=profile.access_token,
            refresh_token=profile.refresh_token,
        )
        await self.audit.log(
            "auth.social_register",
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"provider": profile.provider},
        )
        return user
