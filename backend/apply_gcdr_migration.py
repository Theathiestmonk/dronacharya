#!/usr/bin/env python3

import sys
import os
import sqlite3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_database_path():
    """Get database path from environment or default."""
    # Try SQLite URL from environment
    sqlite_url = os.getenv("SQLITE_URL", "sqlite:///./dronacharya.db")

    # Extract path from sqlite:// URL
    if sqlite_url.startswith("sqlite:///"):
        return sqlite_url[10:]  # Remove 'sqlite:///'
    else:
        return "./dronacharya.db"

def apply_gcdr_migration():
    """Apply the GCDR table creation migration."""
    db_path = get_database_path()

    try:
        # Read the migration SQL
        migration_path = os.path.join(os.path.dirname(__file__), 'migrations', 'create_gcdr_table.sql')
        with open(migration_path, 'r') as f:
            sql_content = f.read()

        print(f"📁 Using database: {db_path}")
        print("📄 Applying GCDR table migration...")
        print("SQL to execute:")
        print(sql_content)
        print("\n" + "="*50)

        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Execute the SQL
        cursor.executescript(sql_content)

        # Commit the changes
        conn.commit()

        print("✅ GCDR migration applied successfully!")
        print("📋 Created table: gcdr")
        print("🔍 You can now use Google Drive OAuth tokens in your admin dashboard.")

    except Exception as e:
        print(f"❌ Error applying GCDR migration: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Make sure the database file exists and is writable")
        print("2. Check that the migrations/create_gcdr_table.sql file exists")
        print("3. You can run the SQL manually using sqlite3:")
        print(f"   sqlite3 {db_path} < migrations/create_gcdr_table.sql")
        return False

    finally:
        if 'conn' in locals():
            conn.close()

    return True

if __name__ == "__main__":
    success = apply_gcdr_migration()
    sys.exit(0 if success else 1)












