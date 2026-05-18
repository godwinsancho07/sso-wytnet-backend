import asyncio
from sqlalchemy import select, func
from app.db.session import SessionLocal, engine
from app.models.user import User
from app.models.plan import CreditLog, Plan

async def check_data():
    async with SessionLocal() as db:
        # 1. Check CreditLog entries for plan_upgrade
        stmt = select(CreditLog).where(CreditLog.event_type == "plan_upgrade")
        logs = (await db.execute(stmt)).scalars().all()
        print(f"Total plan_upgrade logs: {len(logs)}")
        for log in logs:
            print(f"Log ID: {log.id}, Owner ID: {log.owner_id}, Created At: {log.created_at}")

        # 2. Check Users and their plans
        stmt = select(User, Plan).join(Plan, User.plan_id == Plan.id)
        users = (await db.execute(stmt)).all()
        print(f"\nUsers with Plans: {len(users)}")
        for user, plan in users:
            print(f"User: {user.email}, Plan: {plan.name}, Price: {plan.price}")

        # 3. Try the revenue query
        stmt = (
            select(func.count(CreditLog.id), func.sum(Plan.price))
            .join(User, CreditLog.owner_id == User.id)
            .join(Plan, User.plan_id == Plan.id)
            .where(CreditLog.event_type == "plan_upgrade")
        )
        result = await db.execute(stmt)
        total_payments, total_revenue = result.first() or (0, 0)
        print(f"\nRevenue Query Results: payments={total_payments}, revenue={total_revenue}")

if __name__ == "__main__":
    asyncio.run(check_data())
