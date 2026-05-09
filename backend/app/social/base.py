from abc import ABC, abstractmethod
from typing import Optional, Tuple

from app.schemas.social import NormalizedProfile


class BaseSocialProvider(ABC):
    """Contract every social provider adapter must fulfil."""

    name: str  # "google" | "github" | "microsoft" | "linkedin"

    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        """Return the redirect URL that sends the user to the social provider."""

    @abstractmethod
    async def exchange_code(self, code: str) -> dict:
        """Exchange the authorization code for an access token response dict."""

    @abstractmethod
    async def get_user_profile(self, access_token: str) -> dict:
        """Fetch raw user profile data from the provider's API."""

    @abstractmethod
    def normalize_profile(self, raw: dict) -> NormalizedProfile:
        """Convert raw provider profile into a canonical NormalizedProfile."""

    async def fetch_normalized_profile(self, code: str) -> Tuple[NormalizedProfile, dict]:
        """Full flow: exchange code → fetch profile → normalize. Returns (profile, token_data)."""
        token_data = await self.exchange_code(code)
        raw = await self.get_user_profile(token_data["access_token"])
        profile = self.normalize_profile(raw)
        profile.access_token = token_data.get("access_token")
        profile.refresh_token = token_data.get("refresh_token")
        return profile, token_data
