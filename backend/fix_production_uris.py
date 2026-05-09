import sqlite3
import os

# Configuration
DB_PATH = "wytpass.db"  # Adjust if your DB name is different
PRODUCTION_BASE_URL = "https://wytnet.com"

def fix_uris():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Get Project a's client
    cursor.execute("SELECT id, redirect_uris FROM oauth_clients WHERE name LIKE '%Project a%'")
    row = cursor.fetchone()

    if row:
        client_id, current_uris = row
        new_uri = f"{PRODUCTION_BASE_URL}/project-a/dashboard.html"
        
        # Add the new URI if it's not already there
        if new_uri not in current_uris:
            updated_uris = f"{current_uris},{new_uri}" if current_uris else new_uri
            cursor.execute("UPDATE oauth_clients SET redirect_uris = ? WHERE id = ?", (updated_uris, client_id))
            print(f"✅ Added {new_uri} to Project a")
        else:
            print(f"ℹ️ {new_uri} is already registered for Project a")
    else:
        print("❌ Could not find 'Project a' in database")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    fix_uris()
