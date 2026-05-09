"""Runtime configuration service for social identity providers.

DB row overrides env-var defaults. Client secrets are encrypted at rest using
Fernet, with a key derived from settings.secret_key.
"""
import base64
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.models.provider_setting import ProviderSetting
from app.repositories.audit_log import AuditLogRepository

SUPPORTED_PROVIDERS = ("google", "github", "microsoft", "linkedin")


def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(
        hashlib.sha256(settings.secret_key.encode()).digest()
    )
    return Fernet(key)


def _encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def _decrypt_secret(token: Optional[str]) -> Optional[str]:
    if not token:
        return None
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        return None


def _env_defaults(provider: str) -> Dict[str, Any]:
    """Pull defaults from env settings for a provider."""
    if provider == "google":
        return {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
        }
    if provider == "github":
        return {
            "client_id": settings.github_client_id,
            "client_secret": settings.github_client_secret,
            "redirect_uri": settings.github_redirect_uri,
        }
    if provider == "microsoft":
        return {
            "client_id": settings.microsoft_client_id,
            "client_secret": settings.microsoft_client_secret,
            "redirect_uri": settings.microsoft_redirect_uri,
        }
    if provider == "linkedin":
        return {
            "client_id": settings.linkedin_client_id,
            "client_secret": settings.linkedin_client_secret,
            "redirect_uri": settings.linkedin_redirect_uri,
        }
    return {"client_id": None, "client_secret": None, "redirect_uri": None}


class ProviderSettingsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_row(self, provider: str) -> Optional[ProviderSetting]:
        stmt = select(ProviderSetting).where(ProviderSetting.provider == provider)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_provider_config(self, provider: str) -> Dict[str, Any]:
        """Resolve effective config for the provider — DB row beats env vars."""
        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported provider: {provider}")

        env = _env_defaults(provider)
        row = await self._get_row(provider)

        if row is None:
            return {
                "provider": provider,
                "is_enabled": False,
                "client_id": env["client_id"],
                "client_secret": env["client_secret"],
                "redirect_uri": env["redirect_uri"],
                "source": "env",
                "configured": bool(env["client_id"] and env["client_secret"]),
            }

        client_id = row.client_id or env["client_id"]
        decrypted_secret = _decrypt_secret(row.client_secret_encrypted)
        client_secret = decrypted_secret or env["client_secret"]
        redirect_uri = row.redirect_uri or env["redirect_uri"]

        return {
            "provider": provider,
            "is_enabled": row.is_enabled,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "source": "db",
            "configured": bool(client_id and client_secret),
        }

    async def list_providers(self) -> List[Dict[str, Any]]:
        """All 4 providers with status — never returns the secret."""
        out: List[Dict[str, Any]] = []
        for provider in SUPPORTED_PROVIDERS:
            cfg = await self.get_provider_config(provider)
            row = await self._get_row(provider)
            env = _env_defaults(provider)
            out.append({
                "provider": provider,
                "is_enabled": cfg["is_enabled"],
                "configured": cfg["configured"],
                "client_id": cfg["client_id"],
                "redirect_uri": cfg["redirect_uri"],
                "env_redirect_uri": env["redirect_uri"],
                "has_secret": bool(cfg["client_secret"]),
                "source": cfg["source"],
                "updated_at": row.updated_at.isoformat() if row and row.updated_at else None,
                "updated_by_user_id": row.updated_by_user_id if row else None,
            })
        return out

    async def update_provider(
        self,
        provider: str,
        actor_id: str,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        is_enabled: Optional[bool] = None,
    ) -> Dict[str, Any]:
        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported provider: {provider}")

        row = await self._get_row(provider)
        now = datetime.now(timezone.utc)
        if row is None:
            row = ProviderSetting(
                provider=provider,
                is_enabled=is_enabled if is_enabled is not None else False,
                client_id=client_id,
                client_secret_encrypted=_encrypt_secret(client_secret) if client_secret else None,
                redirect_uri=redirect_uri,
                updated_at=now,
                updated_by_user_id=actor_id,
            )
            self.db.add(row)
        else:
            if client_id is not None:
                row.client_id = client_id or None
            if client_secret:
                # Empty string means "leave current" — only update on truthy
                row.client_secret_encrypted = _encrypt_secret(client_secret)
            if redirect_uri is not None:
                row.redirect_uri = redirect_uri or None
            if is_enabled is not None:
                row.is_enabled = is_enabled
            row.updated_at = now
            row.updated_by_user_id = actor_id

        await self.db.flush()

        audit = AuditLogRepository(self.db)
        await audit.log(
            event_type="provider.updated",
            user_id=actor_id,
            metadata={
                "provider": provider,
                "changed": {
                    "client_id": client_id is not None,
                    "client_secret": bool(client_secret),
                    "redirect_uri": redirect_uri is not None,
                    "is_enabled": is_enabled,
                },
            },
        )
        await self.db.commit()
        return await self.get_provider_config(provider)

    async def enable_provider(self, provider: str, actor_id: str) -> Dict[str, Any]:
        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported provider: {provider}")

        row = await self._get_row(provider)
        now = datetime.now(timezone.utc)
        if row is None:
            row = ProviderSetting(
                provider=provider,
                is_enabled=True,
                updated_at=now,
                updated_by_user_id=actor_id,
            )
            self.db.add(row)
        else:
            row.is_enabled = True
            row.updated_at = now
            row.updated_by_user_id = actor_id
        await self.db.flush()

        audit = AuditLogRepository(self.db)
        await audit.log(
            event_type="provider.updated",
            user_id=actor_id,
            metadata={"provider": provider, "action": "enabled"},
        )
        await self.db.commit()
        return await self.get_provider_config(provider)

    async def disable_provider(self, provider: str, actor_id: str) -> Dict[str, Any]:
        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported provider: {provider}")

        row = await self._get_row(provider)
        now = datetime.now(timezone.utc)
        if row is None:
            row = ProviderSetting(
                provider=provider,
                is_enabled=False,
                updated_at=now,
                updated_by_user_id=actor_id,
            )
            self.db.add(row)
        else:
            row.is_enabled = False
            row.updated_at = now
            row.updated_by_user_id = actor_id
        await self.db.flush()

        audit = AuditLogRepository(self.db)
        await audit.log(
            event_type="provider.updated",
            user_id=actor_id,
            metadata={"provider": provider, "action": "disabled"},
        )
        await self.db.commit()
        return await self.get_provider_config(provider)


async def get_provider_config(db: AsyncSession, provider: str) -> Dict[str, Any]:
    """Module-level convenience wrapper."""
    return await ProviderSettingsService(db).get_provider_config(provider)
