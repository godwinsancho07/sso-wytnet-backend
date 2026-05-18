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
# @limiter.limit("10/minute")
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
    db: DB,
    session_token: Annotated[Optional[str], Cookie()] = None,
) -> MessageResponse:
    """Log out the current user by revoking their session and clearing cookies.
    This endpoint does not require authentication so that users can log out even if their token is expired.
    """
    if session_token:
        from app.repositories.session import SessionRepository
        from app.repositories.audit_log import AuditLogRepository
        
        session_repo = SessionRepository(db)
        session_obj = await session_repo.get_by_token(session_token)
        
        if session_obj:
            await session_repo.revoke(session_token)
            
            # Log audit if possible
            audit_repo = AuditLogRepository(db)
            await audit_repo.log(
                "auth.logout", 
                user_id=session_obj.user_id,
                ip_address=get_client_ip(request),
                user_agent=request.headers.get("User-Agent")
            )
            await db.commit()

    response.delete_cookie("session_token", path="/")
    response.delete_cookie("access_token", path="/")
    # Also set headers to prevent any caching of the logout response itself
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
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
async def get_me(response: Response, current_user: CurrentUser, db: DB) -> UserRead:
    # Prevent browser caching of user identity
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    
    # Calculate credits used
    from app.models.plan import CreditLog
    from sqlalchemy import select, func
    stmt = select(func.sum(CreditLog.credits_change)).where(
        CreditLog.owner_id == current_user.id,
        CreditLog.event_type == "trust_login"
    )
    result = await db.execute(stmt)
    credits_used = abs(result.scalar() or 0)
    
    # Add to user object for schema validation
    current_user.credits_used = credits_used
    
    # ENSURE PLAN IS PRESENT: Auto-assign correct default based on role (Developer vs User)
    from app.models.plan import Plan, PlanType
    from app.permissions.checker import get_user_roles
    
    user_roles = await get_user_roles(db, current_user)
    # Developers (App Admins and Super Admins) get DEVELOPER plans, regular users get USER plans
    is_developer = "app_admin" in user_roles or "super_admin" in user_roles
    target_type = PlanType.DEVELOPER if is_developer else PlanType.USER
    
    # Auto-fix: if no plan OR wrong plan type for their role (e.g. app_admin having a USER plan)
    if not current_user.plan_id or (current_user.plan and current_user.plan.type != target_type):
        plan_res = await db.execute(
            select(Plan).where(Plan.type == target_type, Plan.is_default == True)
        )
        default_plan = plan_res.scalar_one_or_none()
        
        # Fallback if no explicit default found for that type
        if not default_plan:
            plan_res = await db.execute(select(Plan).where(Plan.type == target_type))
            default_plan = plan_res.scalars().first()
            
        if default_plan:
            current_user.plan_id = default_plan.id
            current_user.plan = default_plan
            await db.commit()

    if current_user.plan:
        current_user.plan.credits_used = credits_used
        
    return UserRead.model_validate(current_user)


@router.get("/me/permissions")
async def get_my_permissions(response: Response, current_user: CurrentUser, db: DB) -> dict:
    """Return roles + permissions + owned client IDs for the current user.
    Used by frontend to drive UI (which menu items, which dashboard, etc)."""
    # Prevent browser caching of permissions
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    
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
