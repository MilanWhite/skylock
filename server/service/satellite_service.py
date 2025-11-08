from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import math

from sgp4.api import Satrec, jday

from server.model.repository import fetch_all_tles


def _jd_from_datetime(when: datetime):
    """Return Julian date as a single float (JD) from a UTC datetime.

    Uses sgp4.api.jday to get jd and fr and returns jd + fr.
    """
    jd, fr = jday(
        when.year,
        when.month,
        when.day,
        when.hour,
        when.minute,
        when.second + when.microsecond / 1_000_000.0,
    )
    return jd + fr


def _gmst_rad_from_jd(jd: float) -> float:
    """Compute Greenwich Mean Sidereal Time (radians) from Julian Date.

    This uses the IAU 1982 expression (sufficient for typical SGP4 use).
    """
    # Julian centuries from J2000.0
    T = (jd - 2451545.0) / 36525.0
    # GMST in degrees
    gmst_deg = (
        280.46061837
        + 360.98564736629 * (jd - 2451545.0)
        + 0.000387933 * T * T
        - (T ** 3) / 38710000.0
    )
    # Normalize
    gmst_deg = gmst_deg % 360.0
    return math.radians(gmst_deg)


def _eci_to_ecef(position_km: List[float], when: datetime) -> List[float]:
    """Approximate conversion from ECI (assumed TEME/ECI) to ECEF by rotating
    around the Z axis by GMST. Returns position in km in ECEF frame.
    """
    jd = _jd_from_datetime(when)
    theta = _gmst_rad_from_jd(jd)
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    x = position_km[0]
    y = position_km[1]
    z = position_km[2]
    # Rotation about Z: ECEF = Rz(gmst) * ECI
    xe = cos_t * x + sin_t * y
    ye = -sin_t * x + cos_t * y
    ze = z
    return [xe, ye, ze]


def _geodetic_to_ecef(lat_deg: float, lon_deg: float, alt_m: float) -> List[float]:
    """Convert geodetic coordinates (deg, deg, meters) to ECEF (km).

    Uses WGS84 ellipsoid.
    """
    # WGS84 constants
    a = 6378.137  # km
    f = 1.0 / 298.257223563
    e2 = f * (2 - f)

    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    alt_km = alt_m / 1000.0

    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)

    N = a / math.sqrt(1 - e2 * sin_lat * sin_lat)

    x = (N + alt_km) * cos_lat * math.cos(lon)
    y = (N + alt_km) * cos_lat * math.sin(lon)
    z = (N * (1 - e2) + alt_km) * sin_lat
    return [x, y, z]


def find_nearest_satellite(lat_deg: float, lon_deg: float, alt_m: float, when: Optional[datetime] = None, conn=None) -> Optional[Dict[str, Any]]:
    """Find the nearest satellite (Euclidean distance) to the given geodetic
    position at the specified UTC time.

    Args:
      lat_deg, lon_deg: degrees
      alt_m: altitude in meters
      when: datetime (UTC). If None uses now.
      conn: optional DB connection forwarded to repository.

    Returns:
      Dict with satellite info and distance_km, or None if no satellites.
    """
    if when is None:
        when = datetime.now(timezone.utc)

    # Convert user location to ECEF (km)
    user_ecef = _geodetic_to_ecef(lat_deg, lon_deg, alt_m)

    # Fetch TLEs and compute positions
    tles = fetch_all_tles(conn)
    best = None
    best_dist = float("inf")

    for tle in tles:
        satrec = _satrec_from_tle(tle["line1"], tle["line2"])
        if satrec is None:
            continue

        # Compute ECI position at time
        state = _compute_state_for_datetime(satrec, when)
        if state.get("error", 0) != 0:
            # Skip propagations with errors
            continue

        eci_pos = state.get("position_km")
        if not eci_pos:
            continue

        # Convert to ECEF and compute distance
        ecef_pos = _eci_to_ecef(eci_pos, when)
        dx = ecef_pos[0] - user_ecef[0]
        dy = ecef_pos[1] - user_ecef[1]
        dz = ecef_pos[2] - user_ecef[2]
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)

        if dist < best_dist:
            best_dist = dist
            best = {
                "id": tle["id"],
                "name": tle["name"],
                "source": tle.get("source"),
                "fetched_at": tle.get("fetched_at"),
                "when_utc": when.isoformat(),
                "distance_km": dist,
                "position_ecef_km": ecef_pos,
                "position_eci_km": eci_pos,
                "velocity_km_s": state.get("velocity_km_s"),
            }

    return best


# Data querying is intentionally kept in the model/repository layer. The
# service calls `fetch_all_tles()` (which may open its own DB connection).


def _satrec_from_tle(line1: str, line2: str) -> Optional[Satrec]:
    try:
        satrec = Satrec.twoline2rv(line1, line2)
        return satrec
    except Exception:
        return None


def _compute_state_for_datetime(satrec: Satrec, when: datetime) -> Dict[str, Any]:
    """Compute satellite state (position/velocity) at UTC datetime using SGP4.

    Returns a dict with keys: error (int), position_km (list of 3), velocity_km_s (list of 3).
    """
    # Ensure UTC
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    else:
        when = when.astimezone(timezone.utc)

    jd, fr = jday(
        when.year,
        when.month,
        when.day,
        when.hour,
        when.minute,
        when.second + when.microsecond / 1_000_000.0,
    )

    e, r, v = satrec.sgp4(jd, fr)

    return {
        "error": int(e),
        "position_km": [float(x) for x in r],
        "velocity_km_s": [float(x) for x in v],
    }


def get_all_satellite_states(when: Optional[datetime] = None, conn=None) -> List[Dict[str, Any]]:
    """Fetch all TLEs from the DB and compute SGP4 states for each satellite.

    Args:
      when: datetime in UTC to evaluate the SGP4 propagation. If None uses now UTC.
      conn: optional DB connection (sqlite3). If None, a connection will be created.

    Returns:
      A list of dicts, each with satellite metadata and computed state.
    """
    # Fetch TLEs using the data layer (repository). The repository will
    # open/close its own connection if `conn` is None.
    tles = fetch_all_tles(conn)

    if when is None:
        when = datetime.now(timezone.utc)

    results: List[Dict[str, Any]] = []
    for tle in tles:
        satrec = _satrec_from_tle(tle["line1"], tle["line2"])
        if satrec is None:
            results.append({
                "id": tle["id"],
                "name": tle["name"],
                "error": "invalid_tle",
            })
            continue

        state = _compute_state_for_datetime(satrec, when)

        results.append({
            "id": tle["id"],
            "name": tle["name"],
            "source": tle.get("source"),
            "fetched_at": tle.get("fetched_at"),
            "when_utc": when.isoformat(),
            "sgp4_error": state["error"],
            "position_km": state.get("position_km"),
            "velocity_km_s": state.get("velocity_km_s"),
        })

    return results
