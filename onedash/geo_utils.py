from __future__ import annotations

import math
from datetime import datetime, timezone

KM_PER_DEGREE_LAT = 111.32
EARTH_RADIUS_KM = 6371.0088


def in_range_or_none(value: float | None, low: float, high: float) -> bool:
    """NaN-safe range check. The chained comparison fails closed for NaN
    (every comparison with NaN is False), unlike `v < low or v > high`,
    which fails open for NaN and would silently accept it."""
    if value is None:
        return True
    return low <= value <= high


def parse_iso8601_utc(value: str, assume_utc_if_naive: bool = False) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        if not assume_utc_if_naive:
            raise ValueError(
                f"naive timestamp {value!r} requires assume_utc_if_naive=True"
            )
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def bbox_from_radius(
    lat: float, lon: float, radius_km: float
) -> tuple[float, float, float, float]:
    """Returns (south, west, north, east). Longitude wraparound near the
    antimeridian is not handled — out of scope for this app's Brazil-focused
    areas of interest."""
    if not radius_km > 0:
        raise ValueError(f"radius_km must be positive: {radius_km!r}")
    if not in_range_or_none(lat, -90.0, 90.0):
        raise ValueError(f"lat out of range: {lat!r}")

    delta_lat = radius_km / KM_PER_DEGREE_LAT

    cos_lat = max(math.cos(math.radians(lat)), 1e-9)  # guards the pole singularity
    delta_lon = radius_km / (KM_PER_DEGREE_LAT * cos_lat)

    south = max(lat - delta_lat, -90.0)
    north = min(lat + delta_lat, 90.0)
    west = lon - delta_lon
    east = lon + delta_lon
    return south, west, north, east


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c
