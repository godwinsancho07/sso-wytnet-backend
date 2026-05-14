import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine
from app.config import settings
from app.db.base import Base
# Import ALL models here to ensure they are registered with Base.metadata
from app.models import (
    User, SocialAccount, OAuthClient, AuthorizationCode, AccessToken, 
    RefreshToken, Session, Role, Permission, UserRole, RolePermission,
    AuditLog, ClientAdmin, BlockedIP, UserMFA, ProviderSetting, AppBan
)

async def create_tables():
    engine = create_async_engine(settings.database_url, echo=True)
    async with engine.begin() as conn:
        print("Creating missing tables...")
        await conn.run_sync(Base.metadata.create_all)
        print("Done.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_tables())
