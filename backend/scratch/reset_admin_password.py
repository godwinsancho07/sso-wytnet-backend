
import asyncio
from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.user import User
from app.core.security import hash_password

async def reset_password():
    email = "admin@example.com"
    new_password = "aysha@1234"
    
    async with async_session_factory() as session:
        # Find the user
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"User with email {email} not found.")
            return
        
        # Hash and update password
        user.password_hash = hash_password(new_password)
        
        # Also ensure user is active and not locked
        user.is_active = True
        user.failed_login_count = 0
        user.locked_until = None
        
        await session.commit()
        print(f"Successfully reset password for {email}")

if __name__ == "__main__":
    asyncio.run(reset_password())
