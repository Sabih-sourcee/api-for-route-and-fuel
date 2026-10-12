"""Orchestrates geocode → OSRM (1 call) → fuel plan → API payload."""

from __future__ import annotations

from .clients import (
    GeocodeError,
    RouteError,
    build_map_url,
    fetch_driving_route,
    geocode_usa,
)
from .geo import encode_polyline
from .optimizer import MPG, MAX_RANGE_MILES, plan_fuel_stops


class RoutePlanningError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def plan_route(start_query: str, finish_query: str) -> dict:
    try:
        start = geocode_usa(start_query)
        finish = geocode_usa(finish_query)
    except GeocodeError as exc:
        raise RoutePlanningError(str(exc), status=400) from exc

    try:
        route = fetch_driving_route(start, finish)
    except RouteError as exc:
        raise RoutePlanningError(str(exc), status=502) from exc

    plan = plan_fuel_stops(route.coordinates, route.distance_miles)

    if not plan.reachable:
        raise RoutePlanningError(plan.notes or "Route not reachable with given fuel constraints", 422)

    fuel_stops = [
        {
            "sequence": s.sequence,
            "opis_id": s.stop.opis_id,
            "name": s.stop.name,
            "address": s.stop.address,
            "city": s.stop.city,
            "state": s.stop.state,
            "lat": s.stop.lat,
            "lng": s.stop.lng,
            "price_per_gallon": s.price_per_gallon,
            "gallons_to_buy": s.gallons_to_buy,
            "cost": s.cost,
            "distance_from_start_miles": s.mile_marker,
        }
        for s in plan.stops
    ]

    # Downsample coordinates for response size while keeping a usable line.
    coords = route.coordinates
    if len(coords) > 400:
        step = max(1, len(coords) // 400)
        sampled = coords[::step]
        if sampled[-1] != coords[-1]:
            sampled.append(coords[-1])
        coords = sampled

    return {
        "start": {
            "query": start_query,
            "label": start.display_name,
            "lat": start.lat,
            "lng": start.lng,
        },
        "finish": {
            "query": finish_query,
            "label": finish.display_name,
            "lat": finish.lat,
            "lng": finish.lng,
        },
        "distance_miles": round(route.distance_miles, 1),
        "duration_hours": round(route.duration_seconds / 3600.0, 2),
        "mpg": MPG,
        "max_range_miles": MAX_RANGE_MILES,
        "total_fuel_gallons": plan.total_fuel_gallons,
        "total_fuel_cost": plan.total_fuel_cost,
        "map_url": build_map_url(start, finish),
        "route": {
            "geometry": {
                "type": "LineString",
                "coordinates": coords,
            },
            "polyline": encode_polyline(coords),
        },
        "fuel_stops": fuel_stops,
        "notes": plan.notes or None,
        "attribution": {
            "routing": "OSRM / OpenStreetMap",
            "geocoding": "Nominatim / OpenStreetMap",
            "fuel_prices": "Assessment CSV",
            "city_coords": "https://github.com/kelvins/US-Cities-Database",
        },
    }
