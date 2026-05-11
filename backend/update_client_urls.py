import asyncio
from sqlalchemy import select, update
from app.db.session import async_session
from app.models.oauth_client import OAuthClient

async def update_client_urls():
    async with async_session() as db:
        # Update Habit Tracking
        await db.execute(
            update(OAuthClient)
            .where(OAuthClient.client_id == 'client_XCCfrYINlTpyDqKD3b1Hsw')
            .values(
                redirect_uris=["http://localhost:3000/habit-tracking/dashboard.html"],
                logo_url=None
            )
        )
        
        # Update Project A
        await db.execute(
            update(OAuthClient)
            .where(OAuthClient.client_id == 'client_xRleoxpBuyHaFScBx2bFQA')
            .values(
                redirect_uris=["http://localhost:3000/project-a/dashboard.html"],
                logo_url=None
            )
        )
        
        await db.commit()
        print("Updated client URLs to localhost:3000")

if __name__ == "__main__":
    asyncio.run(update_client_urls())
