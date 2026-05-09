from typing import Dict

from app.core.exceptions import AppException
from app.social.base import BaseSocialProvider
from app.social.google import GoogleProvider
from app.social.github import GitHubProvider
from app.social.microsoft import MicrosoftProvider
from app.social.linkedin import LinkedInProvider
from fastapi import status

_PROVIDERS: Dict[str, BaseSocialProvider] = {
    "google": GoogleProvider(),
    "github": GitHubProvider(),
    "microsoft": MicrosoftProvider(),
    "linkedin": LinkedInProvider(),
}


def get_provider(name: str) -> BaseSocialProvider:
    provider = _PROVIDERS.get(name.lower())
    if not provider:
        raise AppException(
            status.HTTP_400_BAD_REQUEST,
            f"Unsupported social provider: {name}",
            "unsupported_provider",
        )
    return provider
