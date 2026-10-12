"""Thin clients for Nominatim geocoding and OSRM routing (free, no API key)."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass

import httpx
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

USER_AGENT = getattr(
    settings,
    "GEO_USER_AGENT",
    "FuelRouteAPI/1.0 (Django assessment; contact: local-dev)",
)
NOMINATIM_URL = getattr(settings, "NOMINATIM_URL", "https://nominatim.openstreetmap.org/search")
OSRM_URL = getattr(settings, "OSRM_URL", "https://router.project-osrm.org")
CACHE_TTL = getattr(settings, "GEO_CACHE_TTL", 60 * 60)


@dataclass(frozen=True)
class LatLng:
    lat: float
    lng: float
    display_name: str = ""


class GeocodeError(Exception):
    pass


class RouteError(Exception):
    pass


def _cache_key(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}:{digest}"


def geocode_usa(query: str) -> LatLng:
    """Geocode a place string, restricted to the USA. Results are cached."""
    cleaned = " ".join(query.strip().split())
    if not cleaned:
        raise GeocodeError("Empty location")

    key = _cache_key("geocode", cleaned.lower())
    cached = cache.get(key)
    if cached:
        return LatLng(**cached)

    params = {
        "q": cleaned,
        "format": "json",
        "limit": 1,
        "countrycodes": "us",
        "addressdetails": 1,
    }
    headers = {"User-Agent": USER_AGENT}

    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.get(NOMINATIM_URL, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        raise GeocodeError(f"Geocoding failed for '{cleaned}': {exc}") from exc

    if not data:
        raise GeocodeError(f"Could not find location in the USA: '{cleaned}'")

    hit = data[0]
    result = LatLng(
        lat=float(hit["lat"]),
        lng=float(hit["lon"]),
        display_name=hit.get("display_name") or cleaned,
    )
    cache.set(
        key,
        {"lat": result.lat, "lng": result.lng, "display_name": result.display_name},
        CACHE_TTL,
    )
    return result


@dataclass(frozen=True)
class RouteResult:
    distance_miles: float
    duration_seconds: float
    coordinates: list[list[float]]  # GeoJSON [lng, lat]
    start: LatLng
    finish: LatLng


def fetch_driving_route(start: LatLng, finish: LatLng) -> RouteResult:
    """Single OSRM route call. Cached by rounded coordinates."""
    key = _cache_key(
        "osrm",
        f"{start.lat:.5f},{start.lng:.5f}|{finish.lat:.5f},{finish.lng:.5f}",
    )
    cached = cache.get(key)
    if cached:
        return RouteResult(
            distance_miles=cached["distance_miles"],
            duration_seconds=cached["duration_seconds"],
            coordinates=cached["coordinates"],
            start=start,
            finish=finish,
        )

    coords = f"{start.lng},{start.lat};{finish.lng},{finish.lat}"
    url = f"{OSRM_URL}/route/v1/driving/{coords}"
    params = {
        "overview": "full",
        "geometries": "geojson",
        "steps": "false",
    }
    headers = {"User-Agent": USER_AGENT}

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            payload = resp.json()
    except httpx.HTTPError as exc:
        raise RouteError(f"Routing failed: {exc}") from exc

    if payload.get("code") != "Ok" or not payload.get("routes"):
        raise RouteError(f"No driving route found ({payload.get('code')})")

    route = payload["routes"][0]
    distance_miles = float(route["distance"]) / 1609.344
    duration_seconds = float(route["duration"])
    coordinates = route["geometry"]["coordinates"]

    cache.set(
        key,
        {
            "distance_miles": distance_miles,
            "duration_seconds": duration_seconds,
            "coordinates": coordinates,
        },
        CACHE_TTL,
    )
    return RouteResult(
        distance_miles=distance_miles,
        duration_seconds=duration_seconds,
        coordinates=coordinates,
        start=start,
        finish=finish,
    )


def build_map_url(start: LatLng, finish: LatLng) -> str:
    """OpenStreetMap directions deep link for the Loom/Postman demo."""
    return (
        "https://www.openstreetmap.org/directions"
        f"?engine=fossgis_osrm_car"
        f"&route={start.lat}%2C{start.lng}%3B{finish.lat}%2C{finish.lng}"
    )
