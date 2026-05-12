from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import (
    UserAlreadyExistsError, InvalidCredentialsError, UserInactiveError,
    UserNotFoundError, InvalidTokenError,
)
from app.core.security import (
    hash_password, verify_password, generate_token,
    create_access_token, create_id_token,
)
from app.models.user import User
from app.repositories.user import UserRepository
from app.repositories.token import AccessTokenRepository, RefreshTokenRepository
from app.repositories.session import SessionRepository
from app.repositories.audit_log import AuditLogRepository
from app.schemas.auth import RegisterRequest, LoginResponse, TokenResponse
from app.services.email import send_verification_email, send_password_reset_email
from app.services.security import SecurityService
from app.services.mfa import MFAService

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, session: AsyncSession):
        self.db = session
        self.users = UserRepository(session)
        self.access_tokens = AccessTokenRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)
        self.sessions = SessionRepository(session)
        self.audit = AuditLogRepository(session)

    async def register(
        self,
        data: RegisterRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> User:
        if await self.users.get_by_email(data.email):
            raise UserAlreadyExistsError()

        # Auto-verify user on creation as requested
        user = await self.users.create_user(
            email=data.email,
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            email_verified=True,
            email_verification_token=None,
        )

        await self.audit.log(
            "user.register",
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"email": user.email, "auto_verified": True},
        )

        return user

    async def login(
        self,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[str, str, str]:
        """Returns (access_token, refresh_token, session_token).

        Raises InvalidCredentialsError("Access denied") if the IP is blocked,
        UserInactiveError("Account is temporarily locked") if the user is
        currently in a lockout window, or the usual auth errors otherwise.

        If the user has MFA enabled, this still issues tokens — the caller
        (or a follow-up endpoint) is responsible for gating the final
        token issuance via verify_login_mfa(). Frontend can detect MFA
        requirement via /v1/me/mfa/status.
        """
        security = SecurityService(self.db)

        # Pre-check: blocked IP
        if await security.is_ip_blocked(ip_address):
            await self.audit.log(
                "auth.login_failed",
                ip_address=ip_address,
                metadata={"email": email, "reason": "ip_blocked"},
            )
            err = InvalidCredentialsError()
            err.detail = "Access denied"
            raise err

        user = await self.users.get_by_email(email)
        if not user or not user.password_hash:
            raise InvalidCredentialsError()

        # Pre-check: account lock
        if SecurityService.is_user_locked(user):
            await self.audit.log(
                "auth.login_failed",
                user_id=user.id,
                ip_address=ip_address,
                metadata={"email": email, "reason": "account_locked"},
            )
            err = UserInactiveError()
            err.detail = "Account is temporarily locked"
            raise err

        if not verify_password(password, user.password_hash):
            await security.record_failed_login(user.id)
            await self.audit.log(
                "auth.login_failed",
                user_id=user.id,
                ip_address=ip_address,
                metadata={"email": email, "reason": "bad_password"},
            )
            raise InvalidCredentialsError()
        if not user.is_active:
            raise UserInactiveError()

        # Successful password — clear any failed-login state
        await security.reset_failed_logins(user.id)

        access_token, refresh_token, session_token = await self._issue_tokens(
            user, scopes=["openid", "profile", "email"],
            client_id="__internal__",
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.audit.log(
            "auth.login",
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return access_token, refresh_token, session_token

    async def verify_login_mfa(self, user_id: str, code: str) -> bool:
        """Gate final token issuance for MFA-enabled accounts."""
        return await MFAService(self.db).verify_totp(user_id, code)

    async def _issue_tokens(
        self,
        user: User,
        scopes: list[str],
        client_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[str, str, str]:
        from app.permissions.checker import get_user_roles
        roles = await get_user_roles(self.db, user)

        access_token_str = create_access_token(
            subject=user.id,
            scopes=scopes,
            client_id=client_id,
            extra={
                "email": user.email,
                "roles": roles,
                "is_superuser": user.is_superuser
            },
        )
        refresh_token_str = generate_token(48)
        session_token_str = generate_token(48)

        now = datetime.now(timezone.utc)

        # Persist access token
        await self.access_tokens.create(
            token=access_token_str,
            user_id=user.id,
            client_id=client_id if client_id != "__internal__" else (
                await self._get_internal_client_id()
            ),
            scopes=scopes,
            expires_at=now + timedelta(minutes=settings.access_token_expire_minutes),
        )

        # Persist refresh token
        await self.refresh_tokens.create(
            token=refresh_token_str,
            user_id=user.id,
            client_id=client_id if client_id != "__internal__" else (
                await self._get_internal_client_id()
            ),
            scopes=scopes,
            expires_at=now + timedelta(days=settings.refresh_token_expire_days),
        )

        # Create session
        device_info = self._parse_device(user_agent)
        await self.sessions.create(
            session_token=session_token_str,
            user_id=user.id,
            device_info=device_info,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=now + timedelta(days=settings.session_expire_days),
        )

        return access_token_str, refresh_token_str, session_token_str

    async def _get_internal_client_id(self) -> str:
        from app.repositories.oauth_client import OAuthClientRepository
        repo = OAuthClientRepository(self.db)
        client = await repo.get_by_client_id("__internal__")
        if client:
            return client.id
        # Create internal client on demand
        from app.core.security import hash_password as hp
        new_client = await repo.create(
            client_id="__internal__",
            client_secret_hash=hp(generate_token(32)),
            app_name="Internal SSO",
            redirect_uris=[settings.frontend_url],
            allowed_scopes=["openid", "profile", "email"],
            is_confidential=False,
            require_pkce=False,
        )
        return new_client.id

    @staticmethod
    def _parse_device(user_agent: Optional[str]) -> Optional[str]:
        if not user_agent:
            return None
        ua = user_agent.lower()
        if "mobile" in ua or "android" in ua or "iphone" in ua:
            return "Mobile"
        if "tablet" in ua or "ipad" in ua:
            return "Tablet"
        return "Desktop"

    async def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        token_obj = await self.refresh_tokens.get_by_token(refresh_token)
        if not token_obj or token_obj.is_revoked or token_obj.is_expired:
            raise InvalidTokenError("Refresh token is invalid or expired")

        user = await self.users.get(token_obj.user_id)
        if not user or not user.is_active:
            raise UserInactiveError()

        # Rotate: revoke old, issue new
        await self.refresh_tokens.revoke(refresh_token)

        from app.permissions.checker import get_user_roles
        roles = await get_user_roles(self.db, user)

        new_access = create_access_token(
            subject=user.id,
            scopes=token_obj.scopes,
            client_id=token_obj.client_id,
            extra={
                "email": user.email,
                "roles": roles,
                "is_superuser": user.is_superuser
            },
        )
        new_refresh = generate_token(48)

        now = datetime.now(timezone.utc)
        await self.refresh_tokens.create(
            token=new_refresh,
            user_id=user.id,
            client_id=token_obj.client_id,
            scopes=token_obj.scopes,
            parent_token_id=token_obj.id,
            expires_at=now + timedelta(days=settings.refresh_token_expire_days),
        )

        return TokenResponse(
            access_token=new_access,
            refresh_token=new_refresh,
            expires_in=settings.access_token_expire_minutes * 60,
        )

    async def verify_email(self, token: str) -> User:
        user = await self.users.get_by_verification_token(token)
        if not user:
            raise InvalidTokenError("Invalid verification token")
        return await self.users.update(
            user.id,
            email_verified=True,
            email_verification_token=None,
        )

    async def forgot_password(self, email: str) -> None:
        user = await self.users.get_by_email(email)
        if not user:
            return  # Silent: don't reveal whether email exists

        reset_token = generate_token(32)
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        await self.users.update(
            user.id,
            password_reset_token=reset_token,
            password_reset_expires=expires,
        )
        try:
            await send_password_reset_email(user.email, user.full_name, reset_token)
        except Exception:
            logger.warning(f"Could not send password reset email to {user.email}")

    async def reset_password(self, token: str, new_password: str) -> User:
        user = await self.users.get_by_reset_token(token)
        if not user:
            raise InvalidTokenError("Invalid reset token")
        if not user.password_reset_expires:
            raise InvalidTokenError("Reset token has no expiry")
        if datetime.now(timezone.utc) > user.password_reset_expires:
            raise InvalidTokenError("Reset token has expired")

        updated = await self.users.update(
            user.id,
            password_hash=hash_password(new_password),
            password_reset_token=None,
            password_reset_expires=None,
        )
        # Invalidate all sessions on password reset
        await self.sessions.revoke_all_for_user(user.id)
        await self.refresh_tokens.revoke_all_for_user(user.id)
        return updated

    async def logout(self, session_token: str, user_id: str) -> None:
        await self.sessions.revoke(session_token)
        await self.audit.log("auth.logout", user_id=user_id)

    async def global_logout(self, user_id: str) -> None:
        await self.sessions.revoke_all_for_user(user_id)
        await self.refresh_tokens.revoke_all_for_user(user_id)
        await self.access_tokens.revoke_all_for_user(user_id)
        await self.audit.log("auth.global_logout", user_id=user_id)

    async def change_password(
        self, user_id: str, current_password: str, new_password: str
    ) -> None:
        user = await self.users.get(user_id)
        if not user or not user.password_hash:
            raise InvalidCredentialsError()
        if not verify_password(current_password, user.password_hash):
            raise InvalidCredentialsError()
        await self.users.update(user_id, password_hash=hash_password(new_password))
        await self.sessions.revoke_all_for_user(user_id)
        await self.refresh_tokens.revoke_all_for_user(user_id)
