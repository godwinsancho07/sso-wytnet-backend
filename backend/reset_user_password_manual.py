import asyncio
from app.db.session import async_session_factory as SessionLocal
from app.models.user import User
from app.core.security import hash_password
from sqlalchemy import select

async def reset_password(email: str, new_password: str):
    async with SessionLocal() as db:
        # Find the user
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"User with email {email} not found.")
            return

        # Hash the new password
        hashed_pwd = hash_password(new_password)
        
        # Update the password
        user.password_hash = hashed_pwd
        await db.commit()
        print(f"Password for {email} has been reset successfully.")

if __name__ == "__main__":
    email = "user@example.com"
    new_password = "aysha@1234"
    asyncio.run(reset_password(email, new_password))
