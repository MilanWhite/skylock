"""Quick local runner to test satellite nearest-neighbor logic (OOP version).

This script uses a sample location on the University of Toronto St. George
campus and prints the nearest satellite found in the local TLE database.

Notes:
- Ensure you have installed dependencies: `python3 -m pip install -r requirements.txt`
- Ensure your SQLite DB at `database/tles.db` is populated (use the repository fetchers).
"""
from datetime import datetime, timezone
import json
import time

from server.model.repository import SqliteTleRepository
from server.service.satellite_service import Sgp4SatelliteService
from server.service.tle_scheduler_service import TleSchedulerService


def pretty_print_satellite(info: dict):
    if info is None:
        print("No satellite found (empty DB or all TLEs invalid).")
        return

    # Restrict printed fields for readability
    out = {
        "id": info.get("id"),
        "name": info.get("name"),
        "source": info.get("source"),
        "when_utc": info.get("when_utc"),
        "distance_km": info.get("distance_km"),
        "position_ecef_km": info.get("position_ecef_km"),
        "velocity_km_s": info.get("velocity_km_s"),
    }

    print(json.dumps(out, indent=2))


def main():
    # Example: UofT St. George campus (approx)
    lat_deg = 43.6625
    lon_deg = -79.3950
    alt_m = 100.0

    # Set up repository and services
    repo = SqliteTleRepository()
    scheduler = TleSchedulerService(repo, tle_group="amateur", interval_seconds=3600)
    service = Sgp4SatelliteService(repo)

    # Start scheduler with initial fetch
    print("\nStarting scheduler and fetching initial data...")
    scheduler.start(initial_fetch=True)

    # Let it run for a moment to ensure initial fetch completes
    time.sleep(2)

    # Find nearest satellite
    when = datetime.now(timezone.utc)
    print(f"\nFinding nearest satellite to ({lat_deg}, {lon_deg}, {alt_m} m) at {when.isoformat()} UTC")
    nearest = service.find_nearest_satellite(lat_deg, lon_deg, alt_m, when=when)
    pretty_print_satellite(nearest)

    # Stop the scheduler
    scheduler.stop()


if __name__ == "__main__":
    main()
