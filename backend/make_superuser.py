import asyncio
import argparse
from app.db.session import async_session_factory as SessionLocal
from app.models.user import User
from app.models.role import Role, UserRole
from sqlalchemy import select

async def make_superuser(email: str):
    async with SessionLocal() as db:
        # 1. Find the user
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"Error: User with email {email} not found.")
            return

        # 2. Set is_superuser flag
        user.is_superuser = True
        print(f"Set is_superuser=True for {email}")

        # 3. Ensure super_admin role exists
        role_result = await db.execute(select(Role).where(Role.name == "super_admin"))
        role = role_result.scalar_one_or_none()
        
        if not role:
            role = Role(name="super_admin", description="Platform Super Administrator")
            db.add(role)
            await db.flush()
            print("Created super_admin role")

        # 4. Assign role to user
        ur_result = await db.execute(
            select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id)
        )
        if not ur_result.scalar_one_or_none():
            user_role = UserRole(user_id=user.id, role_id=role.id)
            db.add(user_role)
            print(f"Assigned super_admin role to {email}")

        await db.commit()
        print(f"Successfully promoted {email} to Super Admin!")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python make_superuser.py <email>")
        sys.exit(1)
    
    email = sys.argv[1]
    asyncio.run(make_superuser(email))
