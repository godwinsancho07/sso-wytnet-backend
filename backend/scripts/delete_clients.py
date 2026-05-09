"""
Delete OAuth clients except for the specified ones.
Run: python -m scripts.delete_clients
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models import OAuthClient

# Clients to KEEP
KEEP_CLIENTS = {
    "Demo Application",
    "test",
    "tsst",
    "Internal SSO",
    "wyute",
}


async def delete_clients(auto_confirm=False):
    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        # Get all clients
        result = await session.execute(select(OAuthClient))
        all_clients = result.scalars().all()

        # Filter clients to delete (get their IDs)
        to_delete_ids = [c.id for c in all_clients if c.app_name not in KEEP_CLIENTS]
        to_delete_names = [c.app_name for c in all_clients if c.app_name not in KEEP_CLIENTS]

        if not to_delete_ids:
            print("No clients to delete.")
            return

        print(f"Will delete {len(to_delete_ids)} client(s):")
        for name in to_delete_names:
            print(f"  - {name}")

        # Confirm before deleting
        if not auto_confirm:
            confirm = input("\nConfirm deletion? (yes/no): ")
            if confirm.lower() != "yes":
                print("Cancelled.")
                return
        else:
            print("\nProceeding with deletion (auto-confirmed)...")

        # Delete clients using async delete
        await session.execute(delete(OAuthClient).where(OAuthClient.id.in_(to_delete_ids)))
        await session.commit()

        for name in to_delete_names:
            print(f"  + Deleted: {name}")

        print("\n---- Deletion complete ----")


if __name__ == "__main__":
    auto_confirm = "--yes" in sys.argv
    asyncio.run(delete_clients(auto_confirm=auto_confirm))
