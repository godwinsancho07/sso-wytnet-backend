import secrets
from typing import List, Optional, Tuple

from fastapi import status
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.security import hash_password
from app.models import AccessToken, RefreshToken
from app.models.oauth_client import OAuthClient
from app.repositories.audit_log import AuditLogRepository
from app.repositories.oauth_client import OAuthClientRepository
from app.schemas.oauth import OAuthClientCreate, OAuthClientUpdate


class ClientService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.clients = OAuthClientRepository(session)
        self.audit = AuditLogRepository(session)

    async def create_client(
        self,
        data: OAuthClientCreate,
        actor_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[OAuthClient, str]:
        # 1. validate (schema-level via Pydantic)
        client_id = f"client_{secrets.token_urlsafe(16)}"
        client_secret = secrets.token_urlsafe(32)

        # 2. state change
        client = await self.clients.create(
            client_id=client_id,
            client_secret_hash=hash_password(client_secret),
            app_name=data.app_name,
            description=data.description,
            logo_url=data.logo_url,
            redirect_uris=data.redirect_uris,
            allowed_scopes=data.allowed_scopes,
            is_confidential=data.is_confidential,
            require_pkce=data.require_pkce,
        )

        # 3. Add admins
        from app.models.client_admin import ClientAdmin
        
        # Always add the creator
        self.session.add(ClientAdmin(user_id=actor_id, client_id=client.id))
        
        # Add specified admin if different
        if data.initial_admin_id and data.initial_admin_id != actor_id:
            self.session.add(ClientAdmin(user_id=data.initial_admin_id, client_id=client.id))
            
        await self.session.flush()

        # 4. audit log (no side-effects step for create)
        await self.audit.log(
            event_type="client.created",
            user_id=actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={
                "actor_id": actor_id,
                "client_id": client_id,
                "app_name": data.app_name,
            },
        )

        return client, client_secret

    async def get_client(self, client_id: str) -> OAuthClient:
        client = await self.clients.get(client_id)
        if not client:
            raise AppException(status.HTTP_404_NOT_FOUND, "Client not found", "client_not_found")
        return client

    async def update_client(
        self,
        client_id: str,
        data: OAuthClientUpdate,
        actor_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> OAuthClient:
        # 1. validate + capture pre-state for diff
        existing = await self.clients.get(client_id)
        if not existing:
            raise AppException(status.HTTP_404_NOT_FOUND, "Client not found", "client_not_found")

        updates = data.model_dump(exclude_none=True)

        # Build diff (changed fields only)
        diff = {}
        for field, new_value in updates.items():
            old_value = getattr(existing, field, None)
            if old_value != new_value:
                diff[field] = {"old": old_value, "new": new_value}

        # 2. state change
        client = await self.clients.update(client_id, **updates)
        if not client:
            raise AppException(status.HTTP_404_NOT_FOUND, "Client not found", "client_not_found")

        # 4. audit log
        await self.audit.log(
            event_type="client.updated",
            user_id=actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={
                "actor_id": actor_id,
                "client_id": client_id,
                "diff": diff,
            },
        )

        return client

    async def delete_client(
        self,
        client_id: str,
        actor_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        # 1. validate
        existing = await self.clients.get(client_id)
        if not existing:
            raise AppException(status.HTTP_404_NOT_FOUND, "Client not found", "client_not_found")

        # 3. side effects FIRST: revoke all access + refresh tokens for this client
        for model in (AccessToken, RefreshToken):
            await self.session.execute(
                update(model).where(model.client_id == client_id).values(is_revoked=True)
            )

        # 2. state change (delete)
        deleted = await self.clients.delete(client_id)
        if not deleted:
            raise AppException(status.HTTP_404_NOT_FOUND, "Client not found", "client_not_found")

        # 4. audit log
        await self.audit.log(
            event_type="client.deleted",
            user_id=actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={
                "actor_id": actor_id,
                "client_id": client_id,
                "app_name": existing.app_name,
            },
        )

    async def rotate_secret(
        self,
        client_id: str,
        actor_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[OAuthClient, str]:
        # 1. validate
        client = await self.clients.get(client_id)
        if not client:
            raise AppException(status.HTTP_404_NOT_FOUND, "Client not found", "client_not_found")

        # 2. state change
        new_secret = secrets.token_urlsafe(32)
        updated = await self.clients.update(
            client_id, client_secret_hash=hash_password(new_secret)
        )

        # 4. audit log (never log the secret itself)
        await self.audit.log(
            event_type="client.secret_rotated",
            user_id=actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={
                "actor_id": actor_id,
                "client_id": client_id,
            },
        )

        return updated, new_secret

    async def list_clients(self, offset: int = 0, limit: int = 50) -> List[OAuthClient]:
        return await self.clients.list_active(offset=offset, limit=limit)
