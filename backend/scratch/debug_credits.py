import asyncio
import os
import sys

# Add the parent directory to sys.path to import app
sys.path.append(os.getcwd())

from sqlalchemy import select, func, union_all
from app.db.session import async_session_maker
from app.models.oauth_client import OAuthClient
from app.models.token import AccessToken, RefreshToken
from app.models.authorization_code import AuthorizationCode

async def debug_credits():
    client_id_str = "client_Qp_NU6L_ltuKCTOfnL4KGg"
    async with async_session_maker() as session:
        # 1. Get client
        stmt = select(OAuthClient).where(OAuthClient.client_id == client_id_str)
        client = (await session.execute(stmt)).scalar_one_or_none()
        
        if not client:
            print(f"Client {client_id_str} not found!")
            return
            
        print(f"App Name: {client.app_name}")
        print(f"App UUID: {client.id}")
        
        # 2. Count tokens
        q1 = select(RefreshToken.user_id).where(RefreshToken.client_id == client.id)
        q2 = select(AccessToken.user_id).where(AccessToken.client_id == client.id)
        q3 = select(AuthorizationCode.user_id).where(AuthorizationCode.client_id == client.id)
        
        r_users = (await session.execute(q1)).scalars().all()
        a_users = (await session.execute(q2)).scalars().all()
        c_users = (await session.execute(q3)).scalars().all()
        
        print(f"Refresh Token Users: {set(r_users)}")
        print(f"Access Token Users: {set(a_users)}")
        print(f"Auth Code Users: {set(c_users)}")
        
        all_unique = set(r_users) | set(a_users) | set(c_users)
        print(f"TOTAL UNIQUE USERS: {len(all_unique)}")
        print(f"Users: {all_unique}")

if __name__ == "__main__":
    asyncio.run(debug_credits())
