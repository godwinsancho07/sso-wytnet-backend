import asyncio
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.plan import CreditLog
from app.models.user import User

async def list_logs():
    async with SessionLocal() as db:
        stmt = select(CreditLog, User.email).join(User, CreditLog.owner_id == User.id).order_by(CreditLog.created_at.desc()).limit(50)
        results = (await db.execute(stmt)).all()
        
        print(f"{'DATE':<25} | {'EMAIL':<30} | {'EVENT TYPE':<20} | {'DESCRIPTION'}")
        print("-" * 100)
        for log, email in results:
            print(f"{log.created_at.isoformat():<25} | {email:<30} | {log.event_type:<20} | {log.description}")

if __name__ == "__main__":
    asyncio.run(list_logs())
