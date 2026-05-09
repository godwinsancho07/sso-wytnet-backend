import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.config import settings
from app.models import User

async def check_user(email: str):
    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with factory() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            print(f"User found: {user.email}")
            print(f"Active: {user.is_active}")
            print(f"Verified: {user.email_verified}")
        else:
            print(f"User {email} not found.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        asyncio.run(check_user(sys.argv[1]))
    else:
        print("Please provide an email address.")
