from typing import Annotated, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.api.deps import CurrentUser, DB
from app.core.exceptions import InvalidClientError, InvalidRedirectUriError, AppException, OAuthError
from app.oauth.flows import OAuthFlowService
from app.oidc.discovery import get_openid_configuration
from app.oidc.jwks import get_jwks_document
from app.repositories.oauth_client import OAuthClientRepository
from app.repositories.token import AccessTokenRepository
from app.schemas.oauth import (
    OAuthAuthorizeRequest, OAuthRevokeRequest, OAuthTokenResponse, OAuthUserInfo,
)

import logging
logger = logging.getLogger(__name__)

router = APIRouter(tags=["oauth"])


@router.get("/.well-known/openid-configuration")
async def openid_configuration():
    return get_openid_configuration()


@router.get("/.well-known/jwks.json")
async def jwks():
    return get_jwks_document()


@router.get("/oauth/authorize")
async def authorize(
    request: Request,
    db: DB,
    response_type: str = "code",
    client_id: str = "",
    redirect_uri: str = "",
    scope: str = "openid",
    state: Optional[str] = None,
    nonce: Optional[str] = None,
    code_challenge: Optional[str] = None,
    code_challenge_method: Optional[str] = None,
    token: Optional[str] = None,
) -> RedirectResponse:
    """Authorization endpoint. Accepts Bearer token or token query param."""
    from app.core.security import decode_access_token
    from app.repositories.token import AccessTokenRepository
    from app.repositories.user import UserRepository
    from jose import JWTError

    # Resolve token from query param, Authorization header, or cookie
    raw_token = token
    if not raw_token:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            raw_token = auth_header[7:]
    if not raw_token:
        raw_token = request.cookies.get("access_token")

    # If no token, redirect to login page
    if not raw_token:
        from app.config.settings import settings
        # Ensure the 'next' URL points to the frontend so cookies are shared
        next_url = f"/oauth/authorize?{request.url.query}"
        login_url = f"{settings.frontend_url}/login?next={quote(next_url, safe='')}"
        return RedirectResponse(login_url)

    try:
        payload = decode_access_token(raw_token)
    except JWTError:
        from app.config.settings import settings
        next_url = f"/oauth/authorize?{request.url.query}"
        login_url = f"{settings.frontend_url}/login?next={quote(next_url, safe='')}"
        return RedirectResponse(login_url)

    from app.repositories.user import UserRepository
    user_id = payload.get("sub")
    user_repo = UserRepository(db)
    current_user = await user_repo.get(user_id)

    auth_req = OAuthAuthorizeRequest(
        response_type=response_type,
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scope,
        state=state,
        nonce=nonce,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
    )

    flow = OAuthFlowService(db)
    client = await flow.validate_authorization_request(auth_req)

    # Check if user is banned from this specific app
    from app.models.app_ban import AppBan
    from sqlalchemy import select, or_
    
    # Check by both client.id (UUID) and the client_id string to be 100% sure
    ban_stmt = select(AppBan).where(
        or_(AppBan.client_id == client.id, AppBan.client_id == client_id),
        AppBan.user_id == current_user.id
    )
    is_banned = (await db.execute(ban_stmt)).scalar_one_or_none()
    
    if is_banned:
        from app.config.settings import settings
        return RedirectResponse(f"{settings.frontend_url}/banned?client_id={client_id}")

    # Check for explicit confirmation (Consent)
    if request.query_params.get("confirm") != "true":
        from app.config.settings import settings
        consent_url = f"{settings.frontend_url}/consent/authorize?{request.url.query}"
        return RedirectResponse(consent_url)

    try:
        code = await flow.create_authorization_code(
            client=client,
            user_id=current_user.id,
            redirect_uri=redirect_uri,
            scopes=auth_req.scopes_list,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            nonce=nonce,
        )
    except AppException as e:
        if getattr(e, 'error_code', None) == "out_of_credits":
            from app.config.settings import settings
            return RedirectResponse(f"{settings.frontend_url}/banned?client_id={client_id}&reason=out_of_credits")
        raise e
    except Exception as e:
        # Fallback for any other error
        logger.error(f"Error in authorize: {e}")
        raise e

    location = f"{redirect_uri}?code={code}"
    if state:
        location += f"&state={state}"

    return RedirectResponse(location, status_code=302)
    
@router.get("/consent/authorize")
async def consent_fallback(request: Request):
    """Fallback to redirect backend consent requests to the frontend."""
    from app.config.settings import settings
    return RedirectResponse(f"{settings.frontend_url}/consent/authorize?{request.url.query}")

@router.post("/oauth/token", response_model=OAuthTokenResponse)
async def token(
    db: DB,
    grant_type: Annotated[str, Form()],
    code: Annotated[Optional[str], Form()] = None,
    redirect_uri: Annotated[Optional[str], Form()] = None,
    client_id: Annotated[Optional[str], Form()] = None,
    client_secret: Annotated[Optional[str], Form()] = None,
    code_verifier: Annotated[Optional[str], Form()] = None,
    refresh_token: Annotated[Optional[str], Form()] = None,
    scope: Annotated[Optional[str], Form()] = None,
) -> OAuthTokenResponse:
    flow = OAuthFlowService(db)

    if grant_type == "authorization_code":
        return await flow.exchange_authorization_code(
            code=code,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier,
        )

    if grant_type == "refresh_token":
        return await flow.refresh_token_grant(
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
        )

    raise InvalidClientError()


@router.get("/oauth/userinfo", response_model=OAuthUserInfo)
async def userinfo(current_user: CurrentUser) -> OAuthUserInfo:
    return OAuthUserInfo(
        sub=current_user.id,
        email=current_user.email,
        email_verified=current_user.email_verified,
        name=current_user.full_name,
        picture=current_user.avatar_url,
    )


@router.post("/oauth/revoke")
async def revoke(body: OAuthRevokeRequest, db: DB) -> dict:
    flow = OAuthFlowService(db)
    await flow.revoke_token(body.token, body.token_type_hint)
    return {"revoked": True}
@router.get("/oauth/client-info")
async def client_info(
    client_id: str, 
    db: DB,
    request: Request
) -> dict:
    """Returns app name and scopes for WytPass consent screen."""
    from app.core.security import decode_access_token
    from app.models.app_ban import AppBan
    from sqlalchemy import select
    from jose import JWTError

    clients = OAuthClientRepository(db)
    client = await clients.get_by_client_id(client_id)
    if not client:
        raise InvalidClientError()

    # Credit Check
    flow = OAuthFlowService(db)
    
    # Get user_id if logged in
    user_id = None
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            
    if token:
        try:
            from app.core.security import decode_access_token
            payload = decode_access_token(token)
            user_id = payload.get("sub")
        except:
            pass
    
    # Check for ban if user is logged in
    is_banned = False
    if user_id:
        try:
            from sqlalchemy import or_
            ban_stmt = select(AppBan).where(
                or_(AppBan.client_id == client.id, AppBan.client_id == client_id),
                AppBan.user_id == user_id
            )
            ban_obj = (await db.execute(ban_stmt)).scalar_one_or_none()
            is_banned = ban_obj is not None
        except (JWTError, Exception):
            pass

    has_credits = await flow.check_credits(client, user_id=user_id)

    return {
        "client_id": client.client_id,
        "app_name": client.app_name,
        "scopes": client.allowed_scopes,
        "logo_url": getattr(client, "logo_url", None),
        "is_banned": is_banned,
        "out_of_credits": not has_credits
    }

@router.get("/oauth/debug-bans")
async def debug_bans(db: DB):
    from app.models.app_ban import AppBan
    from sqlalchemy import select
    res = await db.execute(select(AppBan))
    bans = res.scalars().all()
    return [{"user_id": b.user_id, "client_id": b.client_id} for b in bans]
