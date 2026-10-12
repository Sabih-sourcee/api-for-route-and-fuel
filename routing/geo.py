"""Geodesic helpers and polyline utilities."""

from __future__ import annotations

import math
from typing import Iterable, Sequence

EARTH_RADIUS_MILES = 3958.7613


def haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    rlat1, rlng1, rlat2, rlng2 = map(math.radians, (lat1, lng1, lat2, lng2))
    dlat = rlat2 - rlat1
    dlng = rlng2 - rlng1
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(a))


def encode_polyline(coordinates: Sequence[Sequence[float]], precision: int = 5) -> str:
    """Encode [[lng, lat], ...] GeoJSON-order coords to Google polyline."""
    factor = 10**precision
    result: list[str] = []
    prev_lat = 0
    prev_lng = 0

    def _encode_value(value: int) -> str:
        value = ~(value << 1) if value < 0 else (value << 1)
        chunks = []
        while value >= 0x20:
            chunks.append(chr((0x20 | (value & 0x1F)) + 63))
            value >>= 5
        chunks.append(chr(value + 63))
        return "".join(chunks)

    for lng, lat in coordinates:
        ilat = int(round(lat * factor))
        ilng = int(round(lng * factor))
        result.append(_encode_value(ilat - prev_lat))
        result.append(_encode_value(ilng - prev_lng))
        prev_lat, prev_lng = ilat, ilng
    return "".join(result)


def cumulative_route_miles(
    coordinates: Sequence[Sequence[float]],
) -> list[tuple[float, float, float]]:
    """Return [(lat, lng, miles_from_start), ...] from GeoJSON [lng, lat] list."""
    if not coordinates:
        return []
    points: list[tuple[float, float, float]] = []
    total = 0.0
    prev_lat = coordinates[0][1]
    prev_lng = coordinates[0][0]
    points.append((prev_lat, prev_lng, 0.0))
    for lng, lat in coordinates[1:]:
        total += haversine_miles(prev_lat, prev_lng, lat, lng)
        points.append((lat, lng, total))
        prev_lat, prev_lng = lat, lng
    return points


def project_point_onto_route(
    lat: float,
    lng: float,
    route_points: Sequence[tuple[float, float, float]],
) -> tuple[float, float] | None:
    """
    Find nearest route vertex; return (distance_from_start_miles, distance_to_route_miles).

    Uses a cheap degree-space prune before haversine for speed on long polylines.
    """
    if not route_points:
        return None
    # ~20 miles in degrees at mid-latitudes (corridor is 15 mi; keep headroom)
    max_deg = 0.35
    best_dist = float("inf")
    best_mile = 0.0
    for rlat, rlng, mile in route_points:
        if abs(rlat - lat) > max_deg or abs(rlng - lng) > max_deg:
            continue
        d = haversine_miles(lat, lng, rlat, rlng)
        if d < best_dist:
            best_dist = d
            best_mile = mile
    if best_dist == float("inf"):
        # Fallback: nearest by crude delta if nothing in window
        for rlat, rlng, mile in route_points:
            d = abs(rlat - lat) + abs(rlng - lng)
            if d < best_dist:
                best_dist = d
                best_mile = mile
        # Convert crude winner to miles once
        for rlat, rlng, mile in route_points:
            if mile == best_mile:
                return best_mile, haversine_miles(lat, lng, rlat, rlng)
        return None
    return best_mile, best_dist


def bounding_box(
    coordinates: Iterable[Sequence[float]],
    pad_degrees: float = 0.35,
) -> tuple[float, float, float, float]:
    """Return (min_lat, max_lat, min_lng, max_lng) with padding (~pad_degrees)."""
    lats = [c[1] for c in coordinates]
    lngs = [c[0] for c in coordinates]
    return (
        min(lats) - pad_degrees,
        max(lats) + pad_degrees,
        min(lngs) - pad_degrees,
        max(lngs) + pad_degrees,
    )
