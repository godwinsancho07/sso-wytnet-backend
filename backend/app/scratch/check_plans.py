import asyncio
from sqlalchemy import select
from app.db.database import SessionLocal
from app.models.plan import Plan

async def main():
    async with SessionLocal() as db:
        res = await db.execute(select(Plan))
        plans = res.scalars().all()
        for p in plans:
            print(f"ID: {p.id}, Name: {p.name}, Type: {p.type}, Price: {p.price}, Active: {p.is_active}, Default: {p.is_default}")

if __name__ == "__main__":
    asyncio.run(main())
