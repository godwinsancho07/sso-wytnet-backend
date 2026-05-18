import asyncio
from app.db.session import async_session_factory
from app.models.plan import Plan
from sqlalchemy import select

async def list_plans():
    async with async_session_factory() as db:
        stmt = select(Plan)
        result = await db.execute(stmt)
        plans = result.scalars().all()
        for p in plans:
            print(f"ID: {p.id} | Name: {p.name} | Type: {p.type} | Credits: {p.credits_limit} | Default: {p.is_default}")

if __name__ == "__main__":
    asyncio.run(list_plans())
