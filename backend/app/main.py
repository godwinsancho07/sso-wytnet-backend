# Triggering reload to sync permissions and create missing tables (app_bans)
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
    
    # Auto-fix tables and permissions
    try:
        from sqlalchemy import select
        from app.db.session import engine, async_session_factory
        from app.db.base import Base
        from app.models.role import Permission, Role, RolePermission, UserRole
        from app.models.user import User
        # Ensure all models are imported so Base knows about them
        import app.models 

        # 1. Create missing tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session_factory() as db:
            # Create a debug file to confirm execution
            with open("c:\\Users\\Ayisha\\Music\\sso wytnet2\\backend\\scratch\\seed_log.txt", "w") as f:
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
                for name, res, act in required_perms:
                    result = await db.execute(select(Permission).where(Permission.name == name))
                    if not result.scalar_one_or_none():
                        db.add(Permission(name=name, resource=res, action=act, description=f"Ability to {act} {res}"))
                        f.write(f"Seeded permission: {name}\n")
                await db.flush()

                # 3. Ensure super_admin role exists and has all permissions
                result = await db.execute(select(Role).where(Role.name == "super_admin"))
                super_role = result.scalar_one_or_none()
                if not super_role:
                    super_role = Role(name="super_admin", description="Platform Super Administrator")
                    db.add(super_role)
                    await db.flush()
                    f.write("Created super_admin role\n")

                all_perms = await db.execute(select(Permission))
                for p in all_perms.scalars().all():
                    rp_result = await db.execute(
                        select(RolePermission).where(
                            RolePermission.role_id == super_role.id,
                            RolePermission.permission_id == p.id
                        )
                    )
                    if not rp_result.scalar_one_or_none():
                        db.add(RolePermission(role_id=super_role.id, permission_id=p.id))
                        f.write(f"Granted {p.name} to super_admin\n")

                # 4. Ensure admin users are superusers
                admin_emails = ["admin@example.com", "ayshadhee@gmail.com"] # Adding common admin emails
                for email in admin_emails:
                    result = await db.execute(select(User).where(User.email == email))
                    admin_user = result.scalar_one_or_none()
                    if admin_user:
                        admin_user.is_superuser = True
                        ur_result = await db.execute(
                            select(UserRole).where(
                                UserRole.user_id == admin_user.id,
                                UserRole.role_id == super_role.id
                            )
                        )
                        if not ur_result.scalar_one_or_none():
                            db.add(UserRole(user_id=admin_user.id, role_id=super_role.id))
                            f.write(f"Assigned super_admin role to {email}\n")
                
                # 5. Ensure 'readonly' role is removed (as requested)
                result = await db.execute(select(Role).where(Role.name == "readonly"))
                readonly_role = result.scalar_one_or_none()
                if readonly_role:
                    from sqlalchemy import delete
                    await db.execute(delete(Role).where(Role.id == readonly_role.id))
                    f.write("Deleted 'readonly' role\n")
                
                await db.commit()
                f.write("Successfully synced permissions and roles\n")
    except Exception as e:
        logger.error(f"Failed to sync permissions: {e}")
        with open("c:\\Users\\Ayisha\\Music\\sso wytnet2\\backend\\scratch\\seed_log.txt", "a") as f:
            f.write(f"ERROR: {e}\n")

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
    return {"status": "ok", "service": settings.app_name}
