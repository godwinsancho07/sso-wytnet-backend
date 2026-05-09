import asyncio
import os
from dotenv import load_dotenv
from app.db.session import async_session_factory
from app.models.oauth_client import OAuthClient
from sqlalchemy import select

load_dotenv()

async def list_clients():
    async with async_session_factory() as db:
        res = await db.execute(select(OAuthClient))
        clients = res.scalars().all()
        
        print(f"\n--- Registered Apps ---")
        for c in clients:
            print(f"Name: {c.app_name}")
            print(f"ID:   {c.client_id}")
            print(f"URIs: {c.redirect_uris}")
            print("-" * 30)

if __name__ == "__main__":
    asyncio.run(list_clients())
