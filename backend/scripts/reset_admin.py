"""Force-reset the admin user — guarantees admin@example.com / Admin123!@# works."""
import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.core.security import hash_password
from app.models import User, Role, UserRole

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Admin123!@#"


async def reset():
    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with factory() as session:
        # Find or create admin
        result = await session.execute(select(User).where(User.email == ADMIN_EMAIL))
        user = result.scalar_one_or_none()

        new_hash = hash_password(ADMIN_PASSWORD)

        if user:
            user.password_hash = new_hash
            user.is_active = True
            user.is_superuser = True
            user.email_verified = True
            user.password_reset_token = None
            user.password_reset_expires = None
            print(f"✓ Reset password for existing user {ADMIN_EMAIL}")
        else:
            user = User(
                email=ADMIN_EMAIL,
                password_hash=new_hash,
                full_name="SSO Administrator",
                email_verified=True,
                is_active=True,
                is_superuser=True,
            )
            session.add(user)
            await session.flush()
            print(f"✓ Created admin user {ADMIN_EMAIL}")

        # Ensure admin role assignment
        role_result = await session.execute(select(Role).where(Role.name == "admin"))
        admin_role = role_result.scalar_one_or_none()
        if admin_role:
            ur_result = await session.execute(
                select(UserRole).where(
                    UserRole.user_id == user.id,
                    UserRole.role_id == admin_role.id,
                )
            )
            if not ur_result.scalar_one_or_none():
                session.add(UserRole(user_id=user.id, role_id=admin_role.id))
                print("✓ Assigned admin role")

        await session.commit()

        # Verify the hash works
        from app.core.security import verify_password
        if verify_password(ADMIN_PASSWORD, new_hash):
            print(f"\n✅ Login should now work:")
            print(f"   email:    {ADMIN_EMAIL}")
            print(f"   password: {ADMIN_PASSWORD}")
        else:
            print("⚠ Hash verification failed — bcrypt may be broken")


if __name__ == "__main__":
    asyncio.run(reset())
