from urllib.parse import urlencode

import httpx

from app.config import settings
from app.core.exceptions import SocialProviderError
from app.schemas.social import NormalizedProfile
from app.social.base import BaseSocialProvider

_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"


class LinkedInProvider(BaseSocialProvider):
    name = "linkedin"

    def get_authorization_url(self, state: str) -> str:
        params = {
            "response_type": "code",
            "client_id": settings.linkedin_client_id,
            "redirect_uri": settings.linkedin_redirect_uri,
            "state": state,
            "scope": "openid profile email",
        }
        return f"{_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": settings.linkedin_redirect_uri,
                    "client_id": settings.linkedin_client_id,
                    "client_secret": settings.linkedin_client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        if resp.status_code != 200:
            raise SocialProviderError("linkedin", f"Token exchange failed: {resp.text}")
        return resp.json()

    async def get_user_profile(self, access_token: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                _USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if resp.status_code != 200:
            raise SocialProviderError("linkedin", "Profile fetch failed")
        return resp.json()

    def normalize_profile(self, raw: dict) -> NormalizedProfile:
        return NormalizedProfile(
            provider="linkedin",
            provider_user_id=raw["sub"],
            email=raw.get("email"),
            full_name=raw.get("name"),
            avatar_url=raw.get("picture"),
        )
