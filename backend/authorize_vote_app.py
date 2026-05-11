import asyncio
import os
from dotenv import load_dotenv
from app.db.session import async_session_factory
from app.models.oauth_client import OAuthClient
from sqlalchemy import select, update

load_dotenv()

async def authorize_vote():
    async with async_session_factory() as db:
        client_id = "client_5XUv807ZGIcV5LG0R-CE6w"
        prod_uri = "https://project.dhilip.in/callback"
        
        print(f"--- Authorizing Vote App for Production ---")
        
        res = await db.execute(select(OAuthClient).where(OAuthClient.client_id == client_id))
        client = res.scalar_one_or_none()
        
        if not client:
            print(f"❌ Error: Could not find client with ID {client_id}")
            return
            
        current_uris = list(client.redirect_uris) if client.redirect_uris else []
        
        if prod_uri not in current_uris:
            current_uris.append(prod_uri)
            # Update the client with the new URI
            await db.execute(
                update(OAuthClient)
                .where(OAuthClient.id == client.id)
                .values(redirect_uris=current_uris)
            )
            await db.commit()
            print(f"✅ Successfully authorized: {prod_uri}")
        else:
            print(f"ℹ️ {prod_uri} is already authorized.")

if __name__ == "__main__":
    asyncio.run(authorize_vote())
