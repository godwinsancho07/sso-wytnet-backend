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
    next: Optional[str] = None,
) -> RedirectResponse:
    """Redirect user to the social provider."""
    prov = get_provider(provider)
    state = generate_token(24)

    # Register state in the service's CSRF store
    _state_store[state] = provider

    # Also remember where to return the user after login
    return_to = next or redirect_uri
    if return_to:
        _client_redirect_store[state] = return_to

    auth_url = prov.get_authorization_url(state)
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

    # Pull return_to path before we consume the state
    return_to: Optional[str] = _client_redirect_store.pop(state, None) if state else None

    if error or not code or not state:
        err_msg = error or "cancelled"
        if return_to:
            sep = "&" if "?" in return_to else "?"
            return RedirectResponse(f"{return_to}{sep}error={err_msg}")
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

    # Issue tokens and include the return_to path in the fragment
    params = {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }
    if return_to:
        params["next"] = return_to

    fragment = urlencode(params)
    redirect_url = f"{settings.frontend_url}/social-callback#{fragment}"

    redirect = RedirectResponse(redirect_url)
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
