"""Render the integration markdown personalized for a specific OAuth client."""
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.oauth_client import OAuthClient


_DOCS_PATH = Path(__file__).resolve().parents[3] / "docs" / "INTEGRATION.md"


async def render_for_client(
    client: OAuthClient,
    client_secret: Optional[str] = None,
) -> str:
    """Replace placeholders in the markdown with this client's actual values.

    Pass `client_secret` only at create-time — it's not stored, so subsequent
    downloads omit the secret and tell the user to rotate if lost.
    """
    template = _DOCS_PATH.read_text(encoding="utf-8")

    redirect_uri = client.redirect_uris[0] if client.redirect_uris else "https://yourapp.com/callback"
    backend_url = settings.backend_url.rstrip("/")

    secret_value = client_secret or "<rotate-secret-to-get-new-value>"

    return (
        template
        .replace("__CLIENT_ID__", client.client_id)
        .replace("__CLIENT_SECRET__", secret_value)
        .replace("__REDIRECT_URI__", redirect_uri)
        .replace("__BACKEND_URL__", backend_url)
    )
