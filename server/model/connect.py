import sqlite3
import os
from pathlib import Path

# Define the database path relative to the project root
# (assuming the main script runs from the root)
DB_PATH = "database/tles.db"

def get_db_connection():
    """Establishes a connection to the SQLite database and ensures tables exist."""

    # Ensure the database directory exists
    db_dir = DB_PATH.parent
    if not db_dir.exists():
        print(f"Creating database directory: {db_dir}")
        db_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    
    # Create the tles table if it doesn't exist
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS tles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            line1 TEXT NOT NULL,
            line2 TEXT NOT NULL,
            source TEXT,
            fetched_at TEXT,
            UNIQUE(name, line1, line2)
        )
    ''')
    conn.commit()
    
    return conn