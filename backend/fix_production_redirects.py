import asyncio
import os
from dotenv import load_dotenv
from app.db.session import async_session_factory
from app.models.oauth_client import OAuthClient
from sqlalchemy import select

load_dotenv()

# THE FIX: We are forcing the production URL for your specific app ID
PROD_DOMAIN = "https://wytnet.com"
TARGET_CLIENT_ID = "client_XCCfrYINlTpyDqKD3b1Hsw" # From your error message
TARGET_URI = f"{PROD_DOMAIN}/habit-tracking/dashboard.html"

async def force_fix_redirect():
    async with async_session_factory() as db:
        # Find your specific app
        res = await db.execute(select(OAuthClient).where(OAuthClient.client_id == TARGET_CLIENT_ID))
        client = res.scalar_one_or_none()
        
        if not client:
            print(f"❌ Error: Could not find app with ID {TARGET_CLIENT_ID} in database.")
            return

        print(f"Found App: '{client.app_name}'")
        
        current_uris = list(client.redirect_uris) if client.redirect_uris else []
        
        if TARGET_URI not in current_uris:
            current_uris.append(TARGET_URI)
            client.redirect_uris = current_uris
            await db.commit()
            print(f"✅ SUCCESS: Authorized {TARGET_URI}")
        else:
            print(f"ℹ️ Already Authorized: {TARGET_URI}")
            
        print(f"\nAll allowed URIs for this app: {client.redirect_uris}")

if __name__ == "__main__":
    asyncio.run(force_fix_redirect())
