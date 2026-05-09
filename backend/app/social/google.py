from urllib.parse import urlencode
from typing import Optional

import httpx

from app.config import settings
from app.core.exceptions import SocialProviderError
from app.schemas.social import NormalizedProfile
from app.social.base import BaseSocialProvider

_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


class GoogleProvider(BaseSocialProvider):
    name = "google"

    def get_authorization_url(self, state: str) -> str:
        params = {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "select_account",
        }
        return f"{_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
        if resp.status_code != 200:
            raise SocialProviderError("google", f"Token exchange failed: {resp.text}")
        return resp.json()

    async def get_user_profile(self, access_token: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                _USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if resp.status_code != 200:
            raise SocialProviderError("google", f"Profile fetch failed: {resp.text}")
        return resp.json()

    def normalize_profile(self, raw: dict) -> NormalizedProfile:
        return NormalizedProfile(
            provider="google",
            provider_user_id=raw["sub"],
            email=raw.get("email"),
            full_name=raw.get("name"),
            avatar_url=raw.get("picture"),
        )
