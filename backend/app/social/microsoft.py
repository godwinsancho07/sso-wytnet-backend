from urllib.parse import urlencode

import httpx

from app.config import settings
from app.core.exceptions import SocialProviderError
from app.schemas.social import NormalizedProfile
from app.social.base import BaseSocialProvider


class MicrosoftProvider(BaseSocialProvider):
    name = "microsoft"

    @property
    def _auth_url(self) -> str:
        return f"https://login.microsoftonline.com/{settings.microsoft_tenant_id}/oauth2/v2.0/authorize"

    @property
    def _token_url(self) -> str:
        return f"https://login.microsoftonline.com/{settings.microsoft_tenant_id}/oauth2/v2.0/token"

    def get_authorization_url(self, state: str) -> str:
        params = {
            "client_id": settings.microsoft_client_id,
            "redirect_uri": settings.microsoft_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile User.Read",
            "state": state,
            "response_mode": "query",
        }
        return f"{self._auth_url}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self._token_url,
                data={
                    "code": code,
                    "client_id": settings.microsoft_client_id,
                    "client_secret": settings.microsoft_client_secret,
                    "redirect_uri": settings.microsoft_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
        if resp.status_code != 200:
            raise SocialProviderError("microsoft", f"Token exchange failed: {resp.text}")
        return resp.json()

    async def get_user_profile(self, access_token: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if resp.status_code != 200:
            raise SocialProviderError("microsoft", "Profile fetch failed")
        return resp.json()

    def normalize_profile(self, raw: dict) -> NormalizedProfile:
        email = raw.get("mail") or raw.get("userPrincipalName")
        name_parts = [raw.get("givenName", ""), raw.get("surname", "")]
        full_name = " ".join(p for p in name_parts if p) or raw.get("displayName")
        return NormalizedProfile(
            provider="microsoft",
            provider_user_id=raw["id"],
            email=email,
            full_name=full_name,
            avatar_url=None,
        )
