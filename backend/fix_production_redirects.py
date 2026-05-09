import asyncio
import os
import re
from dotenv import load_dotenv
from app.db.session import async_session_factory
from app.models.oauth_client import OAuthClient
from sqlalchemy import select

load_dotenv()

# Get production domain from .env
PROD_DOMAIN = os.getenv("FRONTEND_URL", "https://wytnet.com").rstrip('/')

def create_slug(name):
    # Convert "Project A" -> "project-a"
    name = name.lower().strip()
    name = re.sub(r'[^a-z0-9\s-]', '', name) # Remove special chars
    name = re.sub(r'[\s-]+', '-', name)      # Replace spaces/hyphens with a single hyphen
    return name

async def fix_all_apps_dynamically():
    async with async_session_factory() as db:
        res = await db.execute(select(OAuthClient))
        clients = res.scalars().all()
        
        print(f"--- Dynamically Authorizing {len(clients)} Apps for {PROD_DOMAIN} ---")
        
        for client in clients:
            if not client.app_name or client.client_id == "__internal__":
                continue
                
            slug = create_slug(client.app_name)
            prod_uri = f"{PROD_DOMAIN}/{slug}/dashboard.html"
            
            current_uris = list(client.redirect_uris) if client.redirect_uris else []
            
            if prod_uri not in current_uris:
                current_uris.append(prod_uri)
                client.redirect_uris = current_uris
                print(f"✅ Authorized: {prod_uri} (for '{client.app_name}')")
            else:
                print(f"ℹ️ Already OK: {prod_uri}")
                
        await db.commit()
        print("\n✨ All apps in your database are now production-ready!")

if __name__ == "__main__":
    asyncio.run(fix_all_apps_dynamically())
