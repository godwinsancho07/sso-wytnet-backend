import asyncio
from app.db.session import async_session_factory as SessionLocal
from app.models.role import Permission, Role, RolePermission
from app.models.user import User, UserRole
from sqlalchemy import select

async def debug_permissions():
    async with SessionLocal() as db:
        print("--- PERMISSIONS ---")
        result = await db.execute(select(Permission))
        perms = result.scalars().all()
        for p in perms:
            print(f"{p.id}: {p.name} ({p.resource}:{p.action})")
        
        print("\n--- ROLES ---")
        result = await db.execute(select(Role))
        roles = result.scalars().all()
        for r in roles:
            print(f"{r.id}: {r.name}")
            # Get permissions for this role
            p_result = await db.execute(
                select(Permission.name)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .where(RolePermission.role_id == r.id)
            )
            role_perms = p_result.scalars().all()
            print(f"  Permissions: {', '.join(role_perms)}")

        print("\n--- USERS ---")
        result = await db.execute(select(User))
        users = result.scalars().all()
        for u in users:
            print(f"{u.id}: {u.email} (superuser: {u.is_superuser})")
            # Get roles for this user
            r_result = await db.execute(
                select(Role.name)
                .join(UserRole, UserRole.role_id == Role.id)
                .where(UserRole.user_id == u.id)
            )
            user_roles = r_result.scalars().all()
            print(f"  Roles: {', '.join(user_roles)}")

if __name__ == "__main__":
    asyncio.run(debug_permissions())
