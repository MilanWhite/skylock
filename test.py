import sqlite3
import random

def delete_random_rows(db_path, table_name, total_rows=12300, batch_size=10):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    rows_deleted = 0

    try:
        while rows_deleted < total_rows:
            # Calculate remaining rows to delete
            remaining = min(batch_size, total_rows - rows_deleted)

            # Delete random rows in batches
            cursor.execute(f"""
                DELETE FROM {table_name}
                WHERE rowid IN (
                    SELECT rowid FROM {table_name}
                    ORDER BY RANDOM()
                    LIMIT {remaining}
                )
            """)

            if cursor.rowcount == 0:
                break

            rows_deleted += cursor.rowcount
            conn.commit()
            print(f"Deleted {cursor.rowcount} rows (Total: {rows_deleted}/{total_rows})")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    db_path = "database/tles.db"  # Update this path if needed
    table_name = "tles"  # Replace with your table name
    delete_random_rows(db_path, table_name)