import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.config import settings
from app.models import User, AuditLog

async def dump_data():
    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with factory() as session:
        print("--- Last 10 Users ---")
        result = await session.execute(select(User).order_by(User.created_at.desc()).limit(10))
        for user in result.scalars().all():
            print(f"User: {user.email}, Created: {user.created_at}")

        print("\n--- Last 20 Audit Logs ---")
        result = await session.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(20))
        for log in result.scalars().all():
            print(f"Log: {log.event_type}, UserID: {log.user_id}, Meta: {log.metadata_}, Created: {log.created_at}")

if __name__ == "__main__":
    asyncio.run(dump_data())
