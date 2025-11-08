import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from server.model.connect import get_db_connection

# Constants required for fetching
CELESTRAK_URL = "https://celestrak.org/NORAD/elements/gp.php"

# SQL for storing (kept from before)
UPSERT_SQL = '''
INSERT INTO tles (name, line1, line2, source, fetched_at)
VALUES (?, ?, ?, ?, ?)
ON CONFLICT(name, line1, line2) DO UPDATE SET
    source=excluded.source,
    fetched_at=excluded.source;
'''

# MARK: Low-level functions

def fetch_tle_group(group: str, timeout=20) -> str:
    """Makes HTTP request to Celestrak to get TLE data."""
    params = { 'GROUP': group, 'FORMAT': 'tle' }
    resp = requests.get(CELESTRAK_URL, params=params, timeout=timeout)
    resp.raise_for_status()
    return resp.text

def parse_tles(text: str):
    """Parse raw TLE text into a list of (name, line1, line2) tuples."""
    lines = [l.rstrip('\n') for l in text.splitlines() if l.strip() != '']
    tles = []
    i = 0
    while i < len(lines) - 1:
        if lines[i].startswith('1 ') and i >= 1:
            name = lines[i-1]
            line1 = lines[i]
            line2 = lines[i+1] if (i+1) < len(lines) else ''
            tles.append((name, line1, line2))
            i += 2
        else:
            if i + 2 < len(lines):
                name = lines[i]
                line1 = lines[i+1]
                line2 = lines[i+2]
                if line1.startswith('1 ') and line2.startswith('2 '):
                    tles.append((name, line1, line2))
                    i += 3
                else:
                    i += 1
            else:
                break
    return tles

def upsert_tles(conn, tles, source: str):
    """Upserts a list of TLE tuples into the database."""
    now = datetime.now(timezone.utc).isoformat()

    try:
        cur = conn.cursor()
        data_to_insert = [
            (name, l1, l2, source, now) for name, l1, l2 in tles
        ]
        cur.executemany(UPSERT_SQL, data_to_insert)
        conn.commit()
    except Exception as e:
        print(f"Error in upsert_tles: {e}")


def fetch_all_tles(conn=None) -> List[Dict[str, Any]]:
    """Return all TLE rows from the database as a list of dicts.

    If conn is None, this function will open its own connection using
    server.model.connect.get_db_connection().
    """
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, line1, line2, source, fetched_at FROM tles"
        )
        rows = cur.fetchall()
        results: List[Dict[str, Any]] = []
        for row in rows:
            results.append({
                "id": row[0],
                "name": row[1],
                "line1": row[2],
                "line2": row[3],
                "source": row[4],
                "fetched_at": row[5],
            })
        return results
    except Exception as e:
        print(f"Error in fetch_all_tles: {e}")
        return []
    finally:
        if close_conn and conn is not None:
            try:
                conn.close()
            except Exception:
                pass








# MARK: High-level function

def fetch_and_store_group(conn, group: str, timeout: int):
    """High-level function: fetches, parses, and stores TLEs for a single group."""
    source_name = f'celestrak:{group}'

    print(f'Fetching group: {group}')

    # 1. Fetch
    text = fetch_tle_group(group, timeout=timeout)

    # 2. Parse
    tles = parse_tles(text)
    print(f'  parsed {len(tles)} TLE entries from group {group}')

    # 3. Store
    upsert_tles(conn, tles, source=source_name)
    print(f'  Successfully stored group {group} in the database.')