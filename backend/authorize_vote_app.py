import asyncio
from app.db.session import async_session_factory as SessionLocal
from app.models.oauth_client import OAuthClient
from sqlalchemy import select

async def authorize_vote():
    async with SessionLocal() as db:
        res = await db.execute(select(OAuthClient).where(OAuthClient.client_id == 'client_5XUv807ZGIcV5LG0R-CE6w'))
        client = res.scalar_one_or_none()
        if client:
            new_uris = list(client.redirect_uris) if client.redirect_uris else []
            new_uri = "http://localhost:5173/callback"
            if new_uri not in new_uris:
                new_uris.append(new_uri)
                client.redirect_uris = new_uris
                await db.commit()
                print(f"✅ Successfully authorized {new_uri} for VoteSmart AI.")
            else:
                print("ℹ️ Redirect URI already authorized.")
        else:
            print("❌ Client not found!")

if __name__ == "__main__":
    asyncio.run(authorize_vote())
