"""Render the integration markdown personalized for a specific OAuth client."""
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.oauth_client import OAuthClient


# Multiple possible paths for the template (Docker vs Local Dev)
_POSSIBLE_PATHS = [
    Path(__file__).resolve().parent.parent / "assets" / "INTEGRATION.md",  # app/assets/INTEGRATION.md
    Path(__file__).resolve().parents[3] / "docs" / "INTEGRATION.md",      # root/docs/INTEGRATION.md
]

def _get_docs_path() -> Path:
    for p in _POSSIBLE_PATHS:
        if p.exists():
            return p
    return _POSSIBLE_PATHS[0] # Fallback to first one even if missing (will throw error later)

_DOCS_PATH = _get_docs_path()
_NEXTJS_DOCS_PATH = _DOCS_PATH.parent / "NEXTJS_INTEGRATION.md"


async def render_for_client(
    client: OAuthClient,
    client_secret: Optional[str] = None,
) -> str:
    """Replace placeholders in the markdown with this client's actual values.

    Pass `client_secret` only at create-time — it's not stored, so subsequent
    downloads omit the secret and tell the user to rotate if lost.
    """
    # Detect if this is a Next.js project using NextAuth
    is_nextjs = any("/api/auth/callback/" in uri for uri in client.redirect_uris)
    
    docs_path = _NEXTJS_DOCS_PATH if (is_nextjs and _NEXTJS_DOCS_PATH.exists()) else _DOCS_PATH
    template = docs_path.read_text(encoding="utf-8")

    redirect_uri = client.redirect_uris[0] if client.redirect_uris else "https://yourapp.com/callback"
    backend_url = settings.backend_url.rstrip("/")

    secret_value = client_secret or "<rotate-secret-to-get-new-value>"

    # Process Next.js specific placeholders if needed
    uris_list = "\n".join([f"  - `{u}`" for u in client.redirect_uris])
    
    base_urls = list(set([u.split("/api/auth/callback/")[0] for u in client.redirect_uris]))
    if not base_urls:
        base_urls = ["http://localhost:3000"]
    
    if len(base_urls) > 1:
        nextauth_url_str = "\n".join([f"# Option {i+1}: {u.startswith('https') and 'Production' or 'Development'}\nNEXTAUTH_URL={u}" for i, u in enumerate(base_urls)])
    else:
        nextauth_url_str = f"NEXTAUTH_URL={base_urls[0]}"

    return (
        template
        .replace("__CLIENT_ID__", client.client_id)
        .replace("__CLIENT_SECRET__", secret_value)
        .replace("__REDIRECT_URI__", redirect_uri)
        .replace("__REDIRECT_URIS_LIST__", uris_list)
        .replace("__NEXTAUTH_URL__", nextauth_url_str)
        .replace("__BACKEND_URL__", backend_url)
        .replace("__APP_NAME__", client.app_name)
    )
