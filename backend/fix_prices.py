import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres:hqg0WKNcFAM3G7kk10SHqHb6UNUqCI7CkeOahy40QVWO9hxop9aNB8Cp8DSfwZs5@72.61.174.129:5432/postgres"

async def main():
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Check current developer plans
        result = await session.execute(text("SELECT id, name, type, price FROM plans WHERE type = 'DEVELOPER'"))
        rows = result.fetchall()
        print("Current Developer Plans:")
        for r in rows:
            print(r)
            
        # Update prices
        await session.execute(text("UPDATE plans SET price = 499.0 WHERE name = 'Growth' AND type = 'DEVELOPER'"))
        await session.execute(text("UPDATE plans SET price = 1499.0 WHERE name = 'Pro' AND type = 'DEVELOPER'"))
        await session.commit()
        print("Successfully updated developer plan prices!")

        # Verify updates
        result = await session.execute(text("SELECT id, name, type, price FROM plans WHERE type = 'DEVELOPER'"))
        rows = result.fetchall()
        print("Updated Developer Plans:")
        for r in rows:
            print(r)

if __name__ == "__main__":
    asyncio.run(main())
