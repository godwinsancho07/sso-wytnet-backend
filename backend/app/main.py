import logging
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
    
    # Auto-fix client URLs to port 3000
    try:
        from app.db.session import async_session
        from app.models.oauth_client import OAuthClient
        from sqlalchemy import update
        async with async_session() as db:
            # Habit Tracking
            await db.execute(
                update(OAuthClient)
                .where(OAuthClient.client_id == 'client_XCCfrYINlTpyDqKD3b1Hsw')
                .values(redirect_uris=[f"{settings.frontend_url}/habit-tracking/dashboard.html"])
            )
            # Project A
            await db.execute(
                update(OAuthClient)
                .where(OAuthClient.client_id == 'client_xRleoxpBuyHaFScBx2bFQA')
                .values(redirect_uris=[f"{settings.frontend_url}/project-a/dashboard.html"])
            )
            await db.commit()
            logger.info("Automatically updated client URLs to port 3000")
    except Exception as e:
        logger.error(f"Failed to auto-update client URLs: {e}")

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
