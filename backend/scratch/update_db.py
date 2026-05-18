import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

# Load env from parent dir
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

DATABASE_URL = os.getenv("DATABASE_URL")

async def update_db():
    if not DATABASE_URL:
        print("DATABASE_URL not found")
        return

    engine = create_async_engine(DATABASE_URL)
    
    async with engine.begin() as conn:
        print("Creating plans table...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS plans (
                id VARCHAR(36) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                type VARCHAR(20) NOT NULL,
                price FLOAT NOT NULL DEFAULT 0.0,
                description TEXT,
                credits_limit INTEGER NOT NULL DEFAULT 0,
                warning_threshold INTEGER NOT NULL DEFAULT 80,
                reset_interval VARCHAR(20) NOT NULL DEFAULT 'NEVER',
                app_registrations_limit INTEGER NOT NULL DEFAULT 0,
                is_default BOOLEAN NOT NULL DEFAULT FALSE,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        print("Adding columns to users...")
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN plan_id VARCHAR(36) REFERENCES plans(id)"))
        except Exception as e:
            print(f"users.plan_id error (likely already exists): {e}")

        print("Adding columns to oauth_clients...")
        try:
            await conn.execute(text("ALTER TABLE oauth_clients ADD COLUMN plan_id VARCHAR(36) REFERENCES plans(id)"))
        except Exception as e:
            print(f"oauth_clients.plan_id error: {e}")
            
        try:
            await conn.execute(text("ALTER TABLE oauth_clients ADD COLUMN credits_used INTEGER DEFAULT 0"))
        except Exception as e:
            print(f"oauth_clients.credits_used error: {e}")
            
        try:
            await conn.execute(text("ALTER TABLE oauth_clients ADD COLUMN warning_email_sent BOOLEAN DEFAULT FALSE"))
        except Exception as e:
            print(f"oauth_clients.warning_email_sent error: {e}")

    print("Done!")

if __name__ == "__main__":
    asyncio.run(update_db())
