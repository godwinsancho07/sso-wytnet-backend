from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse
from typing import Optional
from urllib.parse import urlencode

from app.api.deps import DB, get_client_ip
from app.config import settings
from app.core.security import generate_token
from app.services.auth import AuthService
from app.services.social import SocialAuthService, _state_store
from app.social.factory import get_provider

router = APIRouter(prefix="/auth", tags=["social"])

# Separate store for the client redirect_uri, keyed by the same state token.
# The social service's _state_store handles CSRF validation (state → provider).
# This store handles where to send the user after login (state → redirect_uri).
_client_redirect_store: dict[str, Optional[str]] = {}


@router.get("/{provider}")
async def social_login_redirect(
    provider: str,
    redirect_uri: Optional[str] = None,
) -> RedirectResponse:
    """Redirect user to the social provider.

    Pass ?redirect_uri=<url> to receive tokens back at your app
    instead of the SSO frontend after login.
    """
    prov = get_provider(provider)
    state = generate_token(24)

    # Register state in the service's CSRF store (provider string, as expected)
    _state_store[state] = provider

    # Also remember where to return the user after login
    if redirect_uri:
        _client_redirect_store[state] = redirect_uri

    auth_url = prov.get_authorization_url(state)
    print(f"DEBUG: Redirecting to Google with URL: {auth_url}")
    return RedirectResponse(auth_url)


@router.get("/{provider}/callback")
async def social_login_callback(
    request: Request,
    response: Response,
    provider: str,
    db: DB,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
) -> RedirectResponse:
    """Handle social provider callback and issue SSO tokens."""

    # Pull client redirect_uri before we consume the state (handle_callback pops it)
    client_redirect_uri: Optional[str] = _client_redirect_store.pop(state, None) if state else None

    if error or not code or not state:
        err_msg = error or "cancelled"
        if client_redirect_uri:
            return RedirectResponse(f"{client_redirect_uri}?error={err_msg}")
        return RedirectResponse(f"{settings.frontend_url}/login?error={err_msg}")

    social_service = SocialAuthService(db)
    user = await social_service.handle_callback(
        provider_name=provider,
        code=code,
        state=state,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )

    auth_service = AuthService(db)
    access_token, refresh_token, session_token = await auth_service._issue_tokens(
        user,
        scopes=["openid", "profile", "email"],
        client_id="__internal__",
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )

    # Decide where to send the user
    if client_redirect_uri:
        params = urlencode({
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
        })
        redirect_url = f"{client_redirect_uri}#{params}"
    else:
        redirect_url = (
            f"{settings.frontend_url}/social-callback"
            f"#access_token={access_token}&refresh_token={refresh_token}"
        )

    redirect = RedirectResponse(redirect_url)
    # Prevent browser caching of the redirect containing tokens
    redirect.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    
    redirect.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        max_age=settings.session_expire_days * 86400,
    )
    return redirect
