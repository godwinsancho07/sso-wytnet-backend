import asyncio
from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.app_ban import AppBan

async def check():
    async with async_session_factory() as db:
        res = await db.execute(select(AppBan))
        bans = res.scalars().all()
        print("TOTAL BANS:", len(bans))
        for b in bans:
            print(f"User: {b.user_id} Client: {b.client_id} Reason: {b.reason}")

if __name__ == "__main__":
    asyncio.run(check())
