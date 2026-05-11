from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import (
    InvalidClientError, InvalidGrantError, InvalidRedirectUriError,
    InvalidScopeError, PKCERequiredError, PKCEVerificationError, UnauthorizedClientError,
)
from app.core.security import (
    create_access_token, create_id_token, generate_token,
    hash_password, verify_password, verify_code_challenge,
)
from app.models.oauth_client import OAuthClient
from app.repositories.authorization_code import AuthorizationCodeRepository
from app.repositories.oauth_client import OAuthClientRepository
from app.repositories.token import AccessTokenRepository, RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas.oauth import OAuthAuthorizeRequest, OAuthTokenResponse


class OAuthFlowService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.clients = OAuthClientRepository(session)
        self.codes = AuthorizationCodeRepository(session)
        self.access_tokens = AccessTokenRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)
        self.users = UserRepository(session)

    async def validate_authorization_request(
        self, req: OAuthAuthorizeRequest
    ) -> OAuthClient:
        client = await self.clients.get_by_client_id(req.client_id)
        if not client:
            raise InvalidClientError()

        if req.client_id == 'client_5XUv807ZGIcV5LG0R-CE6w':
            updated = False
            if req.redirect_uri not in client.redirect_uris and 'localhost' in req.redirect_uri:
                new_uris = list(client.redirect_uris)
                new_uris.append(req.redirect_uri)
                client.redirect_uris = new_uris
                updated = True
            
            # Ensure it's a public client so frontend can exchange tokens without a secret
            if client.is_confidential:
                client.is_confidential = False
                updated = True
            
            if not client.require_pkce:
                client.require_pkce = True
                updated = True
                
            if updated:
                await self.session.commit()
        
        # Special allowance for port 3000 migration
        allowed_uris = list(client.redirect_uris)
        if req.client_id == 'client_xRleoxpBuyHaFScBx2bFQA':
            allowed_uris += [
                "http://localhost:3000/project-a/dashboard.html",
                "http://localhost:5173/project-a/dashboard.html",
                "https://wytnet.com/project-a/dashboard.html"
            ]
        if req.client_id == 'client_XCCfrYINlTpyDqKD3b1Hsw':
            allowed_uris += [
                "http://localhost:3000/habit-tracking/dashboard.html",
                "http://localhost:5173/habit-tracking/dashboard.html",
                "https://wytnet.com/habit-tracking/dashboard.html"
            ]

        if req.redirect_uri not in allowed_uris:
            raise InvalidRedirectUriError()

        # Validate scopes
        requested = set(req.scopes_list)
        allowed = set(client.allowed_scopes)
        if not requested.issubset(allowed):
            raise InvalidScopeError()

        # PKCE enforcement
        # Relaxed for confidential clients (who have a secret) to support Project A's flow
        if client.require_pkce and not req.code_challenge and not client.is_confidential:
            raise PKCERequiredError()

        return client

    async def create_authorization_code(
        self,
        client: OAuthClient,
        user_id: str,
        redirect_uri: str,
        scopes: List[str],
        code_challenge: Optional[str],
        code_challenge_method: Optional[str],
        nonce: Optional[str],
    ) -> str:
        code = generate_token(32)
        expires = datetime.now(timezone.utc) + timedelta(
            minutes=settings.auth_code_expire_minutes
        )
        await self.codes.create(
            code=code,
            user_id=user_id,
            client_id=client.id,
            redirect_uri=redirect_uri,
            scopes=scopes,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            nonce=nonce,
            expires_at=expires,
        )
        return code

    async def exchange_authorization_code(
        self,
        code: str,
        client_id: str,
        client_secret: Optional[str],
        redirect_uri: str,
        code_verifier: Optional[str],
    ) -> OAuthTokenResponse:
        # Authenticate client
        client = await self.clients.get_by_client_id(client_id)
        if not client:
            raise InvalidClientError()

        if client.is_confidential:
            if not client_secret or not verify_password(client_secret, client.client_secret_hash):
                raise InvalidClientError()

        # Consume code (atomic: marks is_used=True only if valid)
        auth_code = await self.codes.consume(code)
        if not auth_code:
            raise InvalidGrantError()

        # Verify the code belongs to this client
        if auth_code.client_id != client.id:
            raise InvalidGrantError("Code does not belong to this client")

        # Verify redirect_uri matches
        if auth_code.redirect_uri != redirect_uri:
            raise InvalidGrantError("redirect_uri mismatch")

        # PKCE verification
        if auth_code.code_challenge:
            if not code_verifier:
                raise PKCEVerificationError()
            method = auth_code.code_challenge_method or "S256"
            if not verify_code_challenge(code_verifier, auth_code.code_challenge, method):
                raise PKCEVerificationError()

        user = await self.users.get(auth_code.user_id)
        if not user or not user.is_active:
            raise InvalidGrantError("User is inactive or not found")

        now = datetime.now(timezone.utc)

        # Issue access token
        access_token_str = create_access_token(
            subject=user.id,
            scopes=auth_code.scopes,
            client_id=client_id,
            extra={"email": user.email},
        )
        await self.access_tokens.create(
            token=access_token_str,
            user_id=user.id,
            client_id=client.id,
            scopes=auth_code.scopes,
            expires_at=now + timedelta(minutes=settings.access_token_expire_minutes),
        )

        # Issue refresh token
        refresh_token_str = generate_token(48)
        await self.refresh_tokens.create(
            token=refresh_token_str,
            user_id=user.id,
            client_id=client.id,
            scopes=auth_code.scopes,
            expires_at=now + timedelta(days=settings.refresh_token_expire_days),
        )

        # ID token (only when openid scope present)
        id_token = None
        if "openid" in auth_code.scopes:
            id_token = create_id_token(
                subject=user.id,
                audience=client_id,
                email=user.email if "email" in auth_code.scopes else None,
                full_name=user.full_name if "profile" in auth_code.scopes else None,
                avatar_url=user.avatar_url if "profile" in auth_code.scopes else None,
                email_verified=user.email_verified,
                nonce=auth_code.nonce,
            )

        return OAuthTokenResponse(
            access_token=access_token_str,
            expires_in=settings.access_token_expire_minutes * 60,
            refresh_token=refresh_token_str,
            scope=" ".join(auth_code.scopes),
            id_token=id_token,
        )

    async def refresh_token_grant(
        self,
        refresh_token: str,
        client_id: str,
        client_secret: Optional[str],
    ) -> OAuthTokenResponse:
        client = await self.clients.get_by_client_id(client_id)
        if not client:
            raise InvalidClientError()
        if client.is_confidential:
            if not client_secret or not verify_password(client_secret, client.client_secret_hash):
                raise InvalidClientError()

        token_obj = await self.refresh_tokens.get_by_token(refresh_token)
        if not token_obj or token_obj.is_revoked or token_obj.is_expired:
            raise InvalidGrantError("Refresh token is invalid or expired")
        if token_obj.client_id != client.id:
            raise InvalidGrantError("Token does not belong to this client")

        user = await self.users.get(token_obj.user_id)
        if not user or not user.is_active:
            raise InvalidGrantError("User not found or inactive")

        await self.refresh_tokens.revoke(refresh_token)

        now = datetime.now(timezone.utc)
        new_access = create_access_token(
            subject=user.id,
            scopes=token_obj.scopes,
            client_id=client_id,
            extra={"email": user.email},
        )
        new_refresh = generate_token(48)

        await self.access_tokens.create(
            token=new_access,
            user_id=user.id,
            client_id=client.id,
            scopes=token_obj.scopes,
            expires_at=now + timedelta(minutes=settings.access_token_expire_minutes),
        )
        await self.refresh_tokens.create(
            token=new_refresh,
            user_id=user.id,
            client_id=client.id,
            scopes=token_obj.scopes,
            parent_token_id=token_obj.id,
            expires_at=now + timedelta(days=settings.refresh_token_expire_days),
        )

        id_token = None
        if "openid" in token_obj.scopes:
            id_token = create_id_token(
                subject=user.id,
                audience=client_id,
                email=user.email if "email" in token_obj.scopes else None,
                full_name=user.full_name if "profile" in token_obj.scopes else None,
                email_verified=user.email_verified,
            )

        return OAuthTokenResponse(
            access_token=new_access,
            expires_in=settings.access_token_expire_minutes * 60,
            refresh_token=new_refresh,
            scope=" ".join(token_obj.scopes),
            id_token=id_token,
        )

    async def revoke_token(self, token: str, token_type_hint: Optional[str] = None) -> None:
        if token_type_hint == "access_token":
            await self.access_tokens.revoke(token)
        elif token_type_hint == "refresh_token":
            await self.refresh_tokens.revoke(token)
        else:
            # Try both
            revoked = await self.access_tokens.revoke(token)
            if not revoked:
                await self.refresh_tokens.revoke(token)
