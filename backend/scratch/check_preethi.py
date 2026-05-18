import asyncio
from app.db.session import async_session_factory
from app.models.user import User
from sqlalchemy import select

async def check_user():
    async with async_session_factory() as db:
        stmt = select(User).where(User.full_name == 'preethi')
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            print(f"User: {user.email}")
            print(f"Plan ID: {user.plan_id}")
            print(f"Is Superuser: {user.is_superuser}")
        else:
            print("User 'preethi' not found")

if __name__ == "__main__":
    asyncio.run(check_user())
