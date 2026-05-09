import asyncio
import secrets
from app.db.session import SessionLocal
from app.models.oauth_client import OAuthClient
from app.models.client_admin import ClientAdmin
from app.models.user import User
from app.core.security import hash_password
from sqlalchemy import select

async def seed_apps():
    async with SessionLocal() as db:
        # Get the first user to be the owner
        user_stmt = select(User).limit(1)
        user = (await db.execute(user_stmt)).scalars().first()
        if not user:
            print("No user found to own the apps!")
            return

        apps_to_create = [
            {"name": "Habit Tracking", "desc": "Keep track of your daily habits and goals."},
            {"name": "Regulation Assistant", "desc": "Assistance with regulatory compliance and tracking."}
        ]

        for app_data in apps_to_create:
            client_id = f"client_{secrets.token_urlsafe(16)}"
            client_secret = secrets.token_urlsafe(32)
            
            client = OAuthClient(
                client_id=client_id,
                client_secret_hash=hash_password(client_secret),
                app_name=app_data["name"],
                description=app_data["desc"],
                redirect_uris=["http://localhost:3000/callback"],
                allowed_scopes=["openid", "profile", "email"],
                is_confidential=True,
                require_pkce=False
            )
            db.add(client)
            await db.flush() # Get client.id

            # Assign as admin
            admin = ClientAdmin(user_id=user.id, client_id=client.id)
            db.add(admin)
            
            print(f"Created App: {app_data['name']}")
            print(f"  Client ID: {client_id}")
            print(f"  Client Secret: {client_secret}")

        await db.commit()
        print("\nApps successfully registered in WytPass!")

if __name__ == "__main__":
    asyncio.run(seed_apps())
