"""Quick local runner to test satellite nearest-neighbor logic.

This script uses a sample location on the University of Toronto St. George
campus and prints the nearest satellite found in the local TLE database.

Notes:
- Ensure you have installed dependencies: `python3 -m pip install -r requirements.txt`
- Ensure your SQLite DB at `database/tles.db` is populated (use the repository fetchers).
"""
from datetime import datetime, timezone
import json

from server.service.satellite_service import find_nearest_satellite


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

    when = datetime.now(timezone.utc)

    print(f"Finding nearest satellite to ({lat_deg}, {lon_deg}, {alt_m} m) at {when.isoformat()} UTC")

    nearest = find_nearest_satellite(lat_deg, lon_deg, alt_m, when=when)

    pretty_print_satellite(nearest)


if __name__ == "__main__":
    main()
