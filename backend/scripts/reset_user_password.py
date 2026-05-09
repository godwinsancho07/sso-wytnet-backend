import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.config import settings
from app.models import User
from app.core.security import hash_password

async def reset_password(email: str, new_password: str):
    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with factory() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            user.password_hash = hash_password(new_password)
            user.is_active = True
            user.email_verified = True
            await session.commit()
            print(f"Password for {email} has been successfully reset to: {new_password}")
        else:
            print(f"User {email} not found in the database.")

if __name__ == "__main__":
    email = "dheesanaysha@gmail.com"
    new_password = "Password123!@#"
    
    if len(sys.argv) > 1:
        email = sys.argv[1]
    if len(sys.argv) > 2:
        new_password = sys.argv[2]
        
    asyncio.run(reset_password(email, new_password))
