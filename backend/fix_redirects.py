import asyncio
from app.db.session import SessionLocal
from app.models.oauth_client import OAuthClient
from sqlalchemy import select, update

async def fix_redirects():
    async with SessionLocal() as db:
        res = await db.execute(select(OAuthClient).where(OAuthClient.client_id == 'client_xRleoxpBuyHaFScBx2bFQA'))
        client = res.scalar_one_or_none()
        if client:
            new_uris = list(client.redirect_uris)
            new_uri = "http://localhost:5173/project-a/dashboard.html"
            if new_uri not in new_uris:
                new_uris.append(new_uri)
                client.redirect_uris = new_uris
                await db.commit()
                print(f"Added {new_uri} to allowed redirects.")
            else:
                print("URI already allowed.")

if __name__ == "__main__":
    asyncio.run(fix_redirects())
