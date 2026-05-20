from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy import select, func, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import (
    AppException,
    InvalidClientError, InvalidGrantError, InvalidRedirectUriError,
    InvalidScopeError, PKCERequiredError, PKCEVerificationError, UnauthorizedClientError,
    PermissionDeniedError,
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
from app.models.plan import Plan, ResetInterval
from sqlalchemy import select, or_
from app.services.email import send_email
from app.models.client_admin import ClientAdmin
from app.models.user import User


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

        if req.client_id in ['client_5XUv807ZGIcV5LG0R-CE6w', 'client_Qp_NU6L_ltuKCTOfnL4KGg']:
            updated = False
            if req.redirect_uri not in client.redirect_uris and ('localhost' in req.redirect_uri or 'project.dhilip.in' in req.redirect_uri):
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

    async def check_credits(self, client: OAuthClient, user_id: Optional[str] = None) -> bool:
        """Returns True if client has enough credits to proceed."""
        from app.models.plan import Plan, PlanType
        from app.models.token import RefreshToken, AccessToken
        from app.models.authorization_code import AuthorizationCode
        
        plan = None
        if client.plan_id:
            plan = await self.session.get(Plan, client.plan_id)
            
        if not plan:
            # Fallback to the default developer plan
            stmt = select(Plan).where(Plan.type == PlanType.DEVELOPER, Plan.is_default == True)
            plan = (await self.session.execute(stmt)).scalar_one_or_none()
        
        # Resolve limit from plan or default to 2
        limit = 2
        if plan:
            # If credits_limit is 0, it means unlimited
            limit = plan.credits_limit
            
        if limit == 0:
            return True # Unlimited

            
        print(f"--- STRICT CREDIT CHECK FOR {client.app_name} ---")
        print(f"Target User: {user_id}")
        print(f"Plan Limit: {limit}")

        # 1. Get ALL unique users with their earliest 'created_at' timestamp
        from app.models.token import AccessToken
        from sqlalchemy import func
        
        # We check both client.id (UUID) and client.client_id (string)
        c_ids = [client.id, client.client_id]
        
        try:
            q1 = select(RefreshToken.user_id, RefreshToken.created_at).where(RefreshToken.client_id.in_(c_ids))
            q2 = select(AccessToken.user_id, AccessToken.created_at).where(AccessToken.client_id.in_(c_ids))
            q3 = select(AuthorizationCode.user_id, AuthorizationCode.created_at).where(AuthorizationCode.client_id.in_(c_ids))
            combined_all = union_all(q1, q2, q3).alias("all_auths")
            
            # Group by user_id to find when each user first appeared
            stmt = (
                select(combined_all.c.user_id, func.min(combined_all.c.created_at).label("first_seen"))
                .group_by(combined_all.c.user_id)
                .order_by(func.min(combined_all.c.created_at))
            )
            results = (await self.session.execute(stmt)).all()
        except Exception as e:
            print(f"ERROR in check_credits SQL: {e}")
            return False # Fallback to blocking if DB error occurs
        
        # These are all users who have EVER authorized, in order of when they first came
        all_authorized_users = [r[0] for r in results]
        total_unique = len(all_authorized_users)
        
        print(f"Total users who ever authorized: {total_unique}")
        print(f"Ordered Users: {all_authorized_users}")

        # 2. Define the "Allowed Set" (The first 'limit' users)
        allowed_set = all_authorized_users[:limit]
        print(f"Allowed Set (First {limit}): {allowed_set}")

        # 3. Enforcement
        if not user_id:
            # If no user_id (loading consent screen), block if we are already at or over capacity
            if total_unique >= limit:
                print(f"REJECTED: App is at capacity ({total_unique}/{limit}).")
                return False
            return True

        # Check if current user is in the allowed set
        if user_id in allowed_set:
            print(f"ALLOWED: User {user_id} is in the allowed set.")
            return True
            
        # If not in allowed set, and we are at capacity, block!
        if total_unique >= limit:
            print(f"REJECTED: User {user_id} is NOT in the allowed set and limit {limit} reached.")
            return False

        # If we are under capacity and user is new, allow!
        print(f"ALLOWED: New user {user_id} within limit {limit}.")
        return True

    async def deduct_credit(self, client: OAuthClient, user_id: Optional[str] = None):
        """Logs a credit consumption event for a new user authorization."""
        from app.models.plan import Plan, PlanType, CreditLog
        from app.models.client_admin import ClientAdmin
        from app.models.user import User
        
        plan = None
        if client.plan_id:
            plan = await self.session.get(Plan, client.plan_id)
            
        if not plan:
            # Fallback to the default developer plan
            stmt = select(Plan).where(Plan.type == PlanType.DEVELOPER, Plan.is_default == True)
            plan = (await self.session.execute(stmt)).scalar_one_or_none()

        if not plan or plan.credits_limit == 0:
            return

        # Increment usage counter
        client.credits_used += 1
        
        # Log the event for all admins of this app
        admin_query = select(ClientAdmin.user_id).where(ClientAdmin.client_id == client.id)
        owner_ids = (await self.session.execute(admin_query)).scalars().all()
        
        target_user = None
        if user_id:
            target_user = await self.session.get(User, user_id)
            
        for owner_id in owner_ids:
            log = CreditLog(
                owner_id=owner_id,
                client_id=client.client_id,
                app_name=client.app_name,
                target_user_email=target_user.email if target_user else "Unknown",
                event_type="trust_login",
                description=f"New user {target_user.email if target_user else 'login'} authorized {client.app_name}",
                credits_change=-1
            )
            self.session.add(log)

        # Check for 80% warning
        threshold = plan.credits_limit * (plan.warning_threshold / 100.0)
        if client.credits_used >= threshold and not client.warning_email_sent:
            for owner_id in owner_ids:
                owner = await self.session.get(User, owner_id)
                if not owner: continue
                try:
                    await send_email(
                        to=owner.email,
                        subject=f"Credit Warning: {client.app_name}",
                        html_body=f"""
                        <h2>Credit Usage Warning</h2>
                        <p>Your application <strong>{client.app_name}</strong> has used {plan.warning_threshold}% of its login credits.</p>
                        <p>Current usage: {client.credits_used} / {plan.credits_limit}</p>
                        <p>Please upgrade your plan to avoid service interruption.</p>
                        <p><a href="{settings.frontend_url}/dashboard/plan">Upgrade Plan</a></p>
                        """
                    )
                except Exception:
                    pass 
            client.warning_email_sent = True
        
        await self.session.commit()

    async def check_app_ban(self, user_id: str, client_db_id: str):
        from app.models.app_ban import AppBan
        from sqlalchemy import select
        stmt = select(AppBan).where(AppBan.user_id == user_id, AppBan.client_id == client_db_id)
        ban = (await self.session.execute(stmt)).scalar_one_or_none()
        if ban:
            raise PermissionDeniedError("Access denied: You have been banned from this application.")

    async def is_new_user_for_client(self, client_id_uuid: str, user_id: str, client_id_str: Optional[str] = None) -> bool:
        """Returns True if the user has never authorized this client before."""
        from app.models.token import RefreshToken, AccessToken
        from app.models.authorization_code import AuthorizationCode
        
        # Check for UUID
        stmt1 = select(RefreshToken.id).where(RefreshToken.client_id == client_id_uuid, RefreshToken.user_id == user_id)
        stmt2 = select(AuthorizationCode.id).where(AuthorizationCode.client_id == client_id_uuid, AuthorizationCode.user_id == user_id)
        stmt3 = select(AccessToken.id).where(AccessToken.client_id == client_id_uuid, AccessToken.user_id == user_id)
        
        # Check for String ID if provided
        if client_id_str:
            stmt1 = select(RefreshToken.id).where(or_(RefreshToken.client_id == client_id_uuid, RefreshToken.client_id == client_id_str), RefreshToken.user_id == user_id)
            stmt2 = select(AuthorizationCode.id).where(or_(AuthorizationCode.client_id == client_id_uuid, AuthorizationCode.client_id == client_id_str), AuthorizationCode.user_id == user_id)
            stmt3 = select(AccessToken.id).where(or_(AccessToken.client_id == client_id_uuid, AccessToken.client_id == client_id_str), AccessToken.user_id == user_id)

        has_existing = (await self.session.execute(stmt1.limit(1))).scalar() or \
                       (await self.session.execute(stmt2.limit(1))).scalar() or \
                       (await self.session.execute(stmt3.limit(1))).scalar()
        return not has_existing

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
        await self.check_app_ban(user_id, client.id)
        
        # Check credits
        if not await self.check_credits(client, user_id):
            raise AppException(403, "Access Denied: This application has reached its user limit on the Free plan. The developer needs to upgrade to allow more users.", "out_of_credits")

        # Deduct credit (unique user logic)
        if await self.is_new_user_for_client(client.id, user_id, client.client_id):
            await self.deduct_credit(client, user_id)

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
            extra={
                "email": user.email,
                "name": user.full_name,
                "full_name": user.full_name
            },
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

        await self.check_app_ban(user.id, client.id)

        await self.refresh_tokens.revoke(refresh_token)

        now = datetime.now(timezone.utc)
        new_access = create_access_token(
            subject=user.id,
            scopes=token_obj.scopes,
            client_id=client_id,
            extra={
                "email": user.email,
                "name": user.full_name,
                "full_name": user.full_name
            },
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
