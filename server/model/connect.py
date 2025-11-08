import sqlite3
import os

# Define the database path relative to the project root
# (assuming the main script runs from the root)
DB_PATH = "../database/tles.db"

def get_db_connection():
    """Establishes a connection to the SQLite database."""

    # Ensure the database directory exists
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        print(f"Creating database directory: {db_dir}")
        os.makedirs(db_dir)

    conn = sqlite3.connect(DB_PATH)
    return conn