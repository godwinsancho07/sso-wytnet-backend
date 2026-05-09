import asyncio
from app.db.session import SessionLocal
from app.models.oauth_client import OAuthClient
from sqlalchemy import select, update

async def fix_client():
    async with SessionLocal() as db:
        stmt = update(OAuthClient).where(OAuthClient.client_id == 'client_xRleoxpBuyHaFScBx2bFQA').values(require_pkce=False)
        await db.execute(stmt)
        await db.commit()
        print("Updated client_xRleoxpBuyHaFScBx2bFQA: require_pkce set to False")

if __name__ == "__main__":
    asyncio.run(fix_client())
