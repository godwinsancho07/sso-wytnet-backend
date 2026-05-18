from fastapi import APIRouter

from app.api.v1 import (
    auth,
    social,
    oauth,
    users,
    clients,
    sessions,
    roles,
    admin,
    permissions,
    security,
    providers,
    reports,
    plans,
)

api_router = APIRouter()

# Auth routes
api_router.include_router(auth.router)
api_router.include_router(social.router)

# OAuth2 / OIDC (no prefix — standard paths like /oauth/authorize, /.well-known/...)
api_router.include_router(oauth.router)

# Resource routes
api_router.include_router(users.router, prefix="/v1")
api_router.include_router(clients.router, prefix="/v1")
api_router.include_router(sessions.router, prefix="/v1")
api_router.include_router(roles.router, prefix="/v1")
api_router.include_router(permissions.router, prefix="/v1")
api_router.include_router(admin.router, prefix="/v1")
api_router.include_router(security.router, prefix="/v1")
api_router.include_router(providers.router, prefix="/v1")
api_router.include_router(reports.router, prefix="/v1")
api_router.include_router(plans.router, prefix="/v1/plans", tags=["plans"])
