"""Rename existing admin user from admin@sso.local → admin@example.com."""
import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.config import settings
from app.models import User


async def fix():
    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with factory() as session:
        result = await session.execute(select(User).where(User.email == "admin@sso.local"))
        user = result.scalar_one_or_none()
        if user:
            await session.execute(
                update(User).where(User.id == user.id).values(email="admin@example.com")
            )
            await session.commit()
            print(f"✓ Updated admin user → admin@example.com")
        else:
            result = await session.execute(select(User).where(User.email == "admin@example.com"))
            if result.scalar_one_or_none():
                print("✓ admin@example.com already exists, nothing to do")
            else:
                print("⚠ No admin user found — run `python -m scripts.seed`")


if __name__ == "__main__":
    asyncio.run(fix())
