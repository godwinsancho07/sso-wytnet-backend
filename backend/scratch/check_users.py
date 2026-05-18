import asyncio
from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.user import User

async def main():
    async with async_session_factory() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        print(f"Total users: {len(users)}")
        for u in users:
            print(f"- {u.email} (Superuser: {u.is_superuser})")

if __name__ == "__main__":
    asyncio.run(main())
