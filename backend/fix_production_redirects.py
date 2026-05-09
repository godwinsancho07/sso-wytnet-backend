import asyncio
import os
from dotenv import load_dotenv
from app.db.session import SessionLocal
from app.models.oauth_client import OAuthClient
from sqlalchemy import select

# Load environment variables from .env file
load_dotenv()

# Dynamically get the base URL from .env (e.g., https://wytnet.com)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip('/')

async def fix_production_redirects():
    async with SessionLocal() as db:
        # Get all registered clients
        res = await db.execute(select(OAuthClient))
        clients = res.scalars().all()
        
        print(f"--- Updating {len(clients)} Apps to use Base URL: {FRONTEND_URL} ---")
        
        for client in clients:
            # Create dynamic slug from the app name
            slug = client.app_name.lower().replace(" ", "-")
            
            # Construct the dynamic redirect URI
            # If the app name is "Habit Tracking", URI becomes "FRONTEND_URL/habit-tracking/dashboard.html"
            prod_uri = f"{FRONTEND_URL}/{slug}/dashboard.html"
            
            # Handle special case for 'project-a' if it doesn't follow the slug pattern
            if "project-a" in slug or "project a" in client.app_name.lower():
                prod_uri = f"{FRONTEND_URL}/project-a/dashboard.html"
            
            current_uris = list(client.redirect_uris) if client.redirect_uris else []
            
            if prod_uri not in current_uris:
                current_uris.append(prod_uri)
                client.redirect_uris = current_uris
                print(f"✅ Authorized: {prod_uri} (for '{client.app_name}')")
            else:
                print(f"ℹ️ Already Exists: {prod_uri}")
                
        await db.commit()
        print("\n✨ Database update complete. All apps are now synchronized with your FRONTEND_URL.")

if __name__ == "__main__":
    asyncio.run(fix_production_redirects())
