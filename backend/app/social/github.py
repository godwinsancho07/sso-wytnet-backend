from urllib.parse import urlencode

import httpx

from app.config import settings
from app.core.exceptions import SocialProviderError
from app.schemas.social import NormalizedProfile
from app.social.base import BaseSocialProvider

_AUTH_URL = "https://github.com/login/oauth/authorize"
_TOKEN_URL = "https://github.com/login/oauth/access_token"
_USER_URL = "https://api.github.com/user"
_EMAIL_URL = "https://api.github.com/user/emails"


class GitHubProvider(BaseSocialProvider):
    name = "github"

    def get_authorization_url(self, state: str) -> str:
        params = {
            "client_id": settings.github_client_id,
            "redirect_uri": settings.github_redirect_uri,
            "scope": "read:user user:email",
            "state": state,
        }
        return f"{_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "redirect_uri": settings.github_redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
        if resp.status_code != 200:
            raise SocialProviderError("github", f"Token exchange failed: {resp.text}")
        data = resp.json()
        if "error" in data:
            raise SocialProviderError("github", data.get("error_description", data["error"]))
        return data

    async def get_user_profile(self, access_token: str) -> dict:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
        }
        async with httpx.AsyncClient() as client:
            user_resp = await client.get(_USER_URL, headers=headers)
            if user_resp.status_code != 200:
                raise SocialProviderError("github", "Profile fetch failed")
            profile = user_resp.json()

            if not profile.get("email"):
                email_resp = await client.get(_EMAIL_URL, headers=headers)
                if email_resp.status_code == 200:
                    emails = email_resp.json()
                    primary = next(
                        (e["email"] for e in emails if e.get("primary") and e.get("verified")),
                        None,
                    )
                    profile["email"] = primary

        return profile

    def normalize_profile(self, raw: dict) -> NormalizedProfile:
        return NormalizedProfile(
            provider="github",
            provider_user_id=str(raw["id"]),
            email=raw.get("email"),
            full_name=raw.get("name") or raw.get("login"),
            avatar_url=raw.get("avatar_url"),
        )
