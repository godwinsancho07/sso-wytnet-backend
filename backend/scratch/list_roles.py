import asyncio
import os
import sys
from sqlalchemy import select

# Add parent dir to path to import app
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.models.role import Role
from app.db.session import async_session

async def list_roles():
    async with async_session() as session:
        result = await session.execute(select(Role))
        roles = result.scalars().all()
        print("Existing Roles:")
        for role in roles:
            print(f"ID: {role.id}, Name: {role.name}, Description: {role.description}")

if __name__ == "__main__":
    asyncio.run(list_roles())
