"""Distances. Pure functions; no PostGIS (distances are computed in Python, which is
fine at the current scale — see README)."""

import math

from app.constants import DISTANCE_DISCLOSURE_STEP_KM

_EARTH_RADIUS_KM = 6371.0088  # mean Earth radius


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two points, in kilometres."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * _EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def disclose_distance_km(distance_km: float, step: float = DISTANCE_DISCLOSURE_STEP_KM) -> float:
    """The distance an acceptor may see before acceptance: rounded to the nearest step,
    and never less than one step, so "0 km" never pinpoints the donor."""
    return max(step, math.floor(distance_km / step + 0.5) * step)  # half-up, not banker's
