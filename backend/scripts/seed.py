"""
Seed RBAC + initial users using the industry-standard model:
- 3 roles: super_admin, app_admin, user
- Permissions follow `resource:action` convention (no `:own` suffix)
- Ownership/scoping is enforced in service layer via client_admins table
Run: python -m scripts.seed
"""
import asyncio
import os
import sys
import secrets

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.core.security import hash_password, generate_token
from app.models import (
    User, Role, Permission, UserRole, RolePermission,
    OAuthClient, ClientAdmin,
)


PERMISSIONS = [
    {"name": "client:create",  "resource": "client",  "action": "create",  "description": "Create OAuth clients"},
    {"name": "client:read",    "resource": "client",  "action": "read",    "description": "View OAuth clients"},
    {"name": "client:edit",    "resource": "client",  "action": "edit",    "description": "Edit OAuth clients"},
    {"name": "client:delete",  "resource": "client",  "action": "delete",  "description": "Delete OAuth clients"},
    {"name": "client:rotate",  "resource": "client",  "action": "rotate",  "description": "Rotate client secrets"},
    {"name": "user:read",      "resource": "user",    "action": "read",    "description": "View users"},
    {"name": "user:edit",      "resource": "user",    "action": "edit",    "description": "Edit users"},
    {"name": "user:suspend",   "resource": "user",    "action": "suspend", "description": "Suspend / activate users"},
    {"name": "user:delete",    "resource": "user",    "action": "delete",  "description": "Delete users"},
    {"name": "role:read",      "resource": "role",    "action": "read",    "description": "View roles"},
    {"name": "role:assign",    "resource": "role",    "action": "assign",  "description": "Assign roles to users"},
    {"name": "role:create",    "resource": "role",    "action": "create",  "description": "Create new roles"},
    {"name": "session:read",   "resource": "session", "action": "read",    "description": "View sessions"},
    {"name": "session:revoke", "resource": "session", "action": "revoke",  "description": "Revoke sessions"},
    {"name": "audit:read",     "resource": "audit",   "action": "read",    "description": "Read audit logs"},
    {"name": "self:read",      "resource": "self",    "action": "read",    "description": "Read own profile/sessions"},
    {"name": "self:edit",      "resource": "self",    "action": "edit",    "description": "Edit own profile"},
]

ROLE_DEFINITIONS = {
    "super_admin": {
        "description": "Platform-wide administrator. Full control.",
        "permissions": [p["name"] for p in PERMISSIONS],
    },
    "app_admin": {
        "description": "Owns one or more OAuth clients. Service layer scopes to their clients.",
        "permissions": [
            "client:read", "client:edit", "client:rotate",
            "user:read",
            "session:read", "session:revoke",
            "audit:read",
            "self:read", "self:edit",
        ],
    },
    "user": {
        "description": "End user. Self-service only.",
        "permissions": ["self:read", "self:edit", "session:read", "session:revoke"],
    },
}

ADMIN_EMAIL = os.getenv("SEED_ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD", "Admin123!@#")
APP_ADMIN_EMAIL = os.getenv("SEED_APP_ADMIN_EMAIL", "appadmin@example.com")
APP_ADMIN_PASSWORD = os.getenv("SEED_APP_ADMIN_PASSWORD", "AppAdmin123!@#")
TEST_USER_EMAIL = os.getenv("SEED_TEST_USER_EMAIL", "user@example.com")
TEST_USER_PASSWORD = os.getenv("SEED_TEST_USER_PASSWORD", "User123!@#")


async def seed():
    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        # Permissions
        perm_map = {}
        for p in PERMISSIONS:
            r = await session.execute(select(Permission).where(Permission.name == p["name"]))
            perm = r.scalar_one_or_none()
            if not perm:
                perm = Permission(**p)
                session.add(perm)
                await session.flush()
                print(f"  + permission   {p['name']}")
            perm_map[p["name"]] = perm

        # Roles + role_permissions
        role_map = {}
        for role_name, role_def in ROLE_DEFINITIONS.items():
            r = await session.execute(select(Role).where(Role.name == role_name))
            role = r.scalar_one_or_none()
            if not role:
                role = Role(name=role_name, description=role_def["description"])
                session.add(role)
                await session.flush()
                print(f"  + role         {role_name}")
            role_map[role_name] = role

            existing = await session.execute(
                select(RolePermission).where(RolePermission.role_id == role.id)
            )
            existing_perm_ids = {rp.permission_id for rp in existing.scalars().all()}
            for perm_name in role_def["permissions"]:
                perm = perm_map[perm_name]
                if perm.id not in existing_perm_ids:
                    session.add(RolePermission(role_id=role.id, permission_id=perm.id))

        # Super admin
        admin_user = await _ensure_user(
            session, ADMIN_EMAIL, ADMIN_PASSWORD, "Platform Administrator", is_superuser=True
        )
        await _ensure_role(session, admin_user, role_map["super_admin"])
        print(f"  ✓ super_admin  {ADMIN_EMAIL}")

        # Internal client
        r = await session.execute(select(OAuthClient).where(OAuthClient.client_id == "__internal__"))
        if not r.scalar_one_or_none():
            session.add(OAuthClient(
                client_id="__internal__",
                client_secret_hash=hash_password(generate_token(32)),
                app_name="Internal SSO",
                redirect_uris=[settings.frontend_url],
                allowed_scopes=["openid", "profile", "email"],
                is_confidential=False,
                require_pkce=False,
            ))

        # Demo client
        r = await session.execute(select(OAuthClient).where(OAuthClient.app_name == "Demo Application"))
        demo_client = r.scalar_one_or_none()
        if not demo_client:
            demo_secret = secrets.token_urlsafe(32)
            demo_client_id_str = f"demo_{secrets.token_urlsafe(12)}"
            demo_client = OAuthClient(
                client_id=demo_client_id_str,
                client_secret_hash=hash_password(demo_secret),
                app_name="Demo Application",
                description="Sample OAuth client owned by app admin",
                redirect_uris=["http://localhost:3001/callback", "http://localhost:8080/callback"],
                allowed_scopes=["openid", "profile", "email"],
            )
            session.add(demo_client)
            await session.flush()
            print(f"  + demo client  client_id={demo_client_id_str}")
            print(f"                client_secret={demo_secret}")

        # App admin
        app_admin = await _ensure_user(
            session, APP_ADMIN_EMAIL, APP_ADMIN_PASSWORD, "App Administrator"
        )
        await _ensure_role(session, app_admin, role_map["app_admin"])
        r = await session.execute(
            select(ClientAdmin).where(
                ClientAdmin.user_id == app_admin.id,
                ClientAdmin.client_id == demo_client.id,
            )
        )
        if not r.scalar_one_or_none():
            session.add(ClientAdmin(user_id=app_admin.id, client_id=demo_client.id))
        print(f"  ✓ app_admin    {APP_ADMIN_EMAIL}  →  owns {demo_client.app_name}")

        # End user
        end_user = await _ensure_user(
            session, TEST_USER_EMAIL, TEST_USER_PASSWORD, "End User"
        )
        await _ensure_role(session, end_user, role_map["user"])
        print(f"  ✓ user         {TEST_USER_EMAIL}")

        await session.commit()
        print("\n──────── Seed complete ────────")
        print(f"  super admin :  {ADMIN_EMAIL}      /  {ADMIN_PASSWORD}")
        print(f"  app admin   :  {APP_ADMIN_EMAIL}  /  {APP_ADMIN_PASSWORD}")
        print(f"  user        :  {TEST_USER_EMAIL}        /  {TEST_USER_PASSWORD}")


async def _ensure_user(session, email, password, full_name, is_superuser=False) -> User:
    r = await session.execute(select(User).where(User.email == email))
    user = r.scalar_one_or_none()
    if user:
        user.password_hash = hash_password(password)
        user.is_active = True
        user.email_verified = True
        user.is_superuser = is_superuser
        await session.flush()
        return user
    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        is_active=True,
        email_verified=True,
        is_superuser=is_superuser,
    )
    session.add(user)
    await session.flush()
    return user


async def _ensure_role(session, user: User, role: Role):
    r = await session.execute(
        select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id)
    )
    if not r.scalar_one_or_none():
        session.add(UserRole(user_id=user.id, role_id=role.id))


if __name__ == "__main__":
    asyncio.run(seed())
