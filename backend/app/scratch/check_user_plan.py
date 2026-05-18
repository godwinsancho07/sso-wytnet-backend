
import asyncio
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.user import User
from app.models.plan import Plan

async def check_user_plan():
    async with SessionLocal() as db:
        stmt = select(User).where(User.email == 'afli23@gmail.com') # from screenshot
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            print(f"User: {user.email}")
            print(f"Plan ID: {user.plan_id}")
            if user.plan_id:
                plan = await db.get(Plan, user.plan_id)
                print(f"Plan: {plan.name if plan else 'None'}")
            else:
                print("No Plan ID set for user")
        else:
            print("User not found")

if __name__ == "__main__":
    asyncio.run(check_user_plan())
