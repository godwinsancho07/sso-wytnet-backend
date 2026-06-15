# Triggering reload to sync permissions and create missing tables (app_bans) - RE-RELOAD-3
print("!!! BACKEND STARTING !!!")
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.router import api_router
from app.config import settings
from app.core.exceptions import AppException, OAuthError
from app.middleware.audit import AuditMiddleware
from app.middleware.rate_limit import limiter

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.keys import _ensure_keys
    _ensure_keys(settings.private_key_path, settings.public_key_path)
    
    # Log all registered routes for debugging
    print("--- REGISTERED ROUTES ---")
    for route in app.routes:
        if hasattr(route, "path"):
            print(f"ROUTE: {route.path}")
    print("-------------------------")

    # Auto-fix tables and permissions
    try:
        from sqlalchemy import select
        from app.db.session import engine, async_session_factory
        from app.db.base import Base
        from app.models.role import Permission, Role, RolePermission, UserRole
        from app.models.user import User
        from app.models.plan import Plan, PlanType, ResetInterval
        # Ensure all models are imported so Base knows about them
        import app.models 

        # 1. Create missing tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session_factory() as db:
            # Create a debug file to confirm execution
            with open("scratch/seed_log.txt", "w") as f:
                f.write(f"Startup tasks at {datetime.now()}\n")
                
                # Check ban count
                from sqlalchemy import func
                from app.models.app_ban import AppBan
                res = await db.execute(select(func.count()).select_from(AppBan))
                f.write(f"App bans in DB: {res.scalar()}\n")
                
                # 1. Define required permissions
                required_perms = [
                    ("user:read", "User Management", "read"),
                    ("user:write", "User Management", "write"),
                    ("user:suspend", "User Management", "suspend"),
                    ("user:delete", "User Management", "delete"),
                    ("role:read", "Role Management", "read"),
                    ("role:create", "Role Management", "create"),
                    ("role:assign", "Role Management", "assign"),
                    ("client:read", "Client Management", "read"),
                    ("client:create", "Client Management", "create"),
                    ("client:edit", "Client Management", "write"),
                    ("client:delete", "Client Management", "delete"),
                ]

                # 2. Ensure permissions exist
                for name, res_name, act in required_perms:
                    result = await db.execute(select(Permission).where(Permission.name == name))
                    if not result.scalar_one_or_none():
                        db.add(Permission(name=name, resource=res_name, action=act, description=f"Ability to {act} {res_name}"))
                        f.write(f"Seeded permission: {name}\n")
                await db.flush()

                # 3. Ensure required roles exist
                required_roles = [
                    ("super_admin", "Platform Super Administrator"),
                    ("app_admin", "Application Administrator"),
                    ("user", "End User"),
                ]
                
                roles_map = {}
                for r_name, r_desc in required_roles:
                    result = await db.execute(select(Role).where(Role.name == r_name))
                    role = result.scalar_one_or_none()
                    if not role:
                        role = Role(name=r_name, description=r_desc)
                        db.add(role)
                        await db.flush()
                        f.write(f"Created role: {r_name}\n")
                    roles_map[r_name] = role

                # 4. Grant permissions to roles
                all_perms = await db.execute(select(Permission))
                perms_list = all_perms.scalars().all()
                
                # Super Admin gets everything
                for p in perms_list:
                    rp_result = await db.execute(
                        select(RolePermission).where(
                            RolePermission.role_id == roles_map["super_admin"].id,
                            RolePermission.permission_id == p.id
                        )
                    )
                    if not rp_result.scalar_one_or_none():
                        db.add(RolePermission(role_id=roles_map["super_admin"].id, permission_id=p.id))
                        f.write(f"Granted {p.name} to super_admin\n")

                # App Admin gets client management permissions
                app_admin_perms = ["client:read", "client:create", "client:edit", "client:delete"]
                for p_name in app_admin_perms:
                    p_obj = next((p for p in perms_list if p.name == p_name), None)
                    if p_obj:
                        rp_result = await db.execute(
                            select(RolePermission).where(
                                RolePermission.role_id == roles_map["app_admin"].id,
                                RolePermission.permission_id == p_obj.id
                            )
                        )
                        if not rp_result.scalar_one_or_none():
                            db.add(RolePermission(role_id=roles_map["app_admin"].id, permission_id=p_obj.id))
                            f.write(f"Granted {p_name} to app_admin\n")

                # 5. Ensure default users exist in development
                if settings.app_env == "development":
                    from app.core.security import hash_password
                    dev_users = [
                        {
                            "email": "admin@example.com",
                            "password": "Admin123!@#",
                            "full_name": "System Admin",
                            "is_superuser": True,
                            "role": "super_admin"
                        },
                        {
                            "email": "appadmin@example.com",
                            "password": "AppAdmin123!@#",
                            "full_name": "App Admin",
                            "is_superuser": False,
                            "role": "app_admin"
                        },
                        {
                            "email": "user@example.com",
                            "password": "User123!@#",
                            "full_name": "End User",
                            "is_superuser": False,
                            "role": "user"
                        }
                    ]

                    for u_data in dev_users:
                        result = await db.execute(select(User).where(User.email == u_data["email"]))
                        user = result.scalar_one_or_none()
                        if not user:
                            user = User(
                                email=u_data["email"],
                                password_hash=hash_password(u_data["password"]),
                                full_name=u_data["full_name"],
                                is_superuser=u_data["is_superuser"],
                                email_verified=True,
                                is_active=True
                            )
                            db.add(user)
                            await db.flush()
                            f.write(f"Created dev user: {u_data['email']}\n")
                        
                        # Ensure role assignment
                        role_obj = roles_map[u_data["role"]]
                        ur_result = await db.execute(
                            select(UserRole).where(
                                UserRole.user_id == user.id,
                                UserRole.role_id == role_obj.id
                            )
                        )
                        if not ur_result.scalar_one_or_none():
                            db.add(UserRole(user_id=user.id, role_id=role_obj.id))
                            f.write(f"Assigned {u_data['role']} role to {u_data['email']}\n")

                # 6. Ensure 'readonly' role is removed (legacy)
                result = await db.execute(select(Role).where(Role.name == "readonly"))
                readonly_role = result.scalar_one_or_none()
                if readonly_role:
                    from sqlalchemy import delete
                    await db.execute(delete(Role).where(Role.id == readonly_role.id))
                    f.write("Deleted legacy 'readonly' role\n")

                # 7. Ensure default plans exist
                
                # Default Developer Plan (Free)
                res = await db.execute(select(Plan).where(Plan.type == PlanType.DEVELOPER, Plan.is_default == True))
                if not res.scalar_one_or_none():
                    db.add(Plan(
                        name="Free",
                        type=PlanType.DEVELOPER,
                        price=0.0,
                        description="Default plan for new apps",
                        credits_limit=2,
                        warning_threshold=80,
                        reset_interval=ResetInterval.NEVER,
                        is_default=True,
                        is_active=True
                    ))
                    f.write("Created default Free developer plan\n")

                # Default User Plan (Basic)
                res = await db.execute(select(Plan).where(Plan.type == PlanType.USER, Plan.is_default == True))
                if not res.scalar_one_or_none():
                    db.add(Plan(
                        name="Basic",
                        type=PlanType.USER,
                        price=0.0,
                        description="Standard user plan",
                        credits_limit=0, # unlimited
                        is_default=True,
                        is_active=True
                    ))
                    f.write("Created default Basic user plan\n")
                
                # Premium User Plan
                res = await db.execute(select(Plan).where(Plan.type == PlanType.USER, Plan.name == "Premium"))
                premium_plan = res.scalar_one_or_none()
                if not premium_plan:
                    db.add(Plan(
                        name="Premium",
                        type=PlanType.USER,
                        price=2.0,
                        description="Full AI assistance suite with unlimited questions",
                        credits_limit=0, # unlimited
                        is_default=False,
                        is_active=True
                    ))
                    f.write("Created Premium user plan\n")
                elif premium_plan.price != 2.0:
                    premium_plan.price = 2.0
                    f.write("Updated Premium user plan price to 2.0\n")
                
                # Delete legacy "Pro" user plan if it exists
                res = await db.execute(select(Plan).where(Plan.type == PlanType.USER, Plan.name == "Pro"))
                pro_user_plan = res.scalar_one_or_none()
                if pro_user_plan:
                    await db.delete(pro_user_plan)
                    f.write("Deleted legacy Pro user plan\n")

                # Dump all plans for debugging
                res_all = await db.execute(select(Plan))
                all_plans = res_all.scalars().all()
                f.write("CURRENT PLANS IN DB:\n")
                for p in all_plans:
                    f.write(f"- ID: {p.id}, Name: '{p.name}', Type: {p.type}, Price: {p.price}, Active: {p.is_active}\n")

                await db.commit()
                f.write("Successfully synced permissions, roles, plans, and dev users\n")
    except Exception as e:
        logger.error(f"Failed to sync permissions: {e}", exc_info=True)
        try:
            with open("scratch/seed_log.txt", "a") as f:
                f.write(f"ERROR: {e}\n")
        except Exception:
            pass


    logger.info("SSO Identity Provider started")
    yield
    logger.info("SSO Identity Provider shutting down")


app = FastAPI(
    title=settings.app_name,
    description="Production-grade SSO Identity Provider",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# ── Middleware ─────────────────────────────────────────────────────────────────

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(AuditMiddleware)

# Force HTTPS scheme behind reverse proxies (Coolify, Nginx, etc.)
@app.middleware("http")
async def force_https_behind_proxy(request: Request, call_next):
    if request.headers.get("x-forwarded-proto") == "https":
        request.scope["scheme"] = "https"
    return await call_next(request)

# Disable caching for all API GET requests to ensure fresh state across logins
@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    if request.method == "GET" and (
        request.url.path.startswith("/v1/") or 
        request.url.path.startswith("/auth/")
    ) and not request.url.path.startswith(("/docs", "/redoc", "/health")):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ── Exception handlers ────────────────────────────────────────────────────────

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    body = {"detail": exc.detail, "error_code": exc.error_code}
    if isinstance(exc, OAuthError):
        body["error"] = exc.oauth_error
        if exc.oauth_description:
            body["error_description"] = exc.oauth_description
    return JSONResponse(status_code=exc.status_code, content=body)


# ── Routes ────────────────────────────────────────────────────────────────────

app.include_router(api_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.app_name, "version": "RELOADED_V1"}
