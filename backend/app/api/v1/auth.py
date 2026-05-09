from fastapi import APIRouter, Cookie, Depends, Request, Response
from typing import Annotated, Optional

from app.api.deps import CurrentUser, DB, get_client_ip
from app.middleware.rate_limit import limiter
from app.schemas.auth import (
    ChangePasswordRequest, ForgotPasswordRequest, LoginRequest,
    LoginResponse, MessageResponse, RefreshRequest, RegisterRequest,
    RegisterResponse, ResetPasswordRequest, TokenResponse, VerifyEmailRequest,
)
from app.schemas.user import UserRead
from app.services.auth import AuthService
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=201)
@limiter.limit("5/minute")
async def register(
    request: Request,
    body: RegisterRequest,
    db: DB,
) -> RegisterResponse:
    service = AuthService(db)
    user = await service.register(
        body,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    return RegisterResponse(
        message="Registration successful. Please verify your email.",
        user_id=user.id,
    )


@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    db: DB,
) -> LoginResponse:
    service = AuthService(db)
    access_token, refresh_token, session_token = await service.login(
        body.email,
        body.password,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )

    # Set session cookie for browser-based flows
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        max_age=settings.session_expire_days * 86400,
    )
    # Set access token cookie for OAuth authorize endpoint
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
        session_token=session_token,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    current_user: CurrentUser,
    db: DB,
    session_token: Annotated[Optional[str], Cookie()] = None,
) -> MessageResponse:
    if session_token:
        service = AuthService(db)
        await service.logout(session_token, current_user.id)

    response.delete_cookie("session_token")
    response.delete_cookie("access_token")
    return MessageResponse(message="Logged out successfully")


@router.post("/logout/all", response_model=MessageResponse)
async def global_logout(
    response: Response,
    current_user: CurrentUser,
    db: DB,
) -> MessageResponse:
    service = AuthService(db)
    await service.global_logout(current_user.id)
    response.delete_cookie("session_token")
    response.delete_cookie("access_token")
    return MessageResponse(message="Logged out from all devices")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: DB) -> TokenResponse:
    service = AuthService(db)
    return await service.refresh_access_token(body.refresh_token)


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(body: VerifyEmailRequest, db: DB) -> MessageResponse:
    service = AuthService(db)
    await service.verify_email(body.token)
    return MessageResponse(message="Email verified successfully")


@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit("3/minute")
async def forgot_password(
    request: Request, body: ForgotPasswordRequest, db: DB
) -> MessageResponse:
    service = AuthService(db)
    await service.forgot_password(body.email)
    return MessageResponse(message="If that email exists, a reset link has been sent")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(body: ResetPasswordRequest, db: DB) -> MessageResponse:
    service = AuthService(db)
    await service.reset_password(body.token, body.new_password)
    return MessageResponse(message="Password reset successfully")


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    body: ChangePasswordRequest,
    current_user: CurrentUser,
    db: DB,
) -> MessageResponse:
    service = AuthService(db)
    await service.change_password(current_user.id, body.current_password, body.new_password)
    return MessageResponse(message="Password changed successfully")


@router.get("/me", response_model=UserRead)
async def get_me(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)


@router.get("/me/permissions")
async def get_my_permissions(current_user: CurrentUser, db: DB) -> dict:
    """Return roles + permissions + owned client IDs for the current user.
    Used by frontend to drive UI (which menu items, which dashboard, etc)."""
    from app.permissions.checker import (
        get_user_permissions, get_user_roles, get_owned_client_ids, is_super_admin,
    )
    return {
        "user_id": current_user.id,
        "email": current_user.email,
        "is_super_admin": await is_super_admin(db, current_user),
        "roles": await get_user_roles(db, current_user),
        "permissions": sorted(await get_user_permissions(db, current_user)),
        "owned_client_ids": await get_owned_client_ids(db, current_user),
    }
