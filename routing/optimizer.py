"""Cost-aware fuel stop planner for a fixed driving route."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from stations.models import FuelStop

from .geo import bounding_box, cumulative_route_miles, project_point_onto_route

MAX_RANGE_MILES = 500.0
MPG = 10.0
CORRIDOR_MILES = 15.0


@dataclass
class RouteStation:
    stop: FuelStop
    mile_marker: float
    distance_to_route_miles: float
    price: float


@dataclass
class PlannedStop:
    sequence: int
    stop: FuelStop
    mile_marker: float
    price_per_gallon: float
    gallons_to_buy: float
    cost: float


@dataclass
class FuelPlan:
    stops: list[PlannedStop]
    total_fuel_gallons: float
    total_fuel_cost: float
    reachable: bool
    notes: str = ""


def _sample_route_points(
    route_points: Sequence[tuple[float, float, float]],
    step_miles: float = 5.0,
) -> list[tuple[float, float, float]]:
    if not route_points:
        return []
    sampled = [route_points[0]]
    last = 0.0
    for pt in route_points[1:]:
        if pt[2] - last >= step_miles:
            sampled.append(pt)
            last = pt[2]
    if sampled[-1] is not route_points[-1]:
        sampled.append(route_points[-1])
    return sampled


def _candidate_stations(
    coordinates: Sequence[Sequence[float]],
    route_points: Sequence[tuple[float, float, float]],
) -> list[RouteStation]:
    min_lat, max_lat, min_lng, max_lng = bounding_box(coordinates, pad_degrees=0.4)
    sampled = _sample_route_points(route_points)
    qs = FuelStop.objects.filter(
        lat__isnull=False,
        lng__isnull=False,
        lat__gte=min_lat,
        lat__lte=max_lat,
        lng__gte=min_lng,
        lng__lte=max_lng,
    ).iterator(chunk_size=2000)

    best: dict[int, RouteStation] = {}
    for stop in qs:
        projected = project_point_onto_route(stop.lat, stop.lng, sampled)
        if projected is None:
            continue
        mile_marker, dist_to_route = projected
        if dist_to_route > CORRIDOR_MILES:
            continue
        price = float(stop.retail_price)
        existing = best.get(stop.opis_id)
        if existing is None or price < existing.price:
            best[stop.opis_id] = RouteStation(
                stop=stop,
                mile_marker=mile_marker,
                distance_to_route_miles=dist_to_route,
                price=price,
            )

    return sorted(best.values(), key=lambda s: s.mile_marker)


def plan_fuel_stops(
    coordinates: Sequence[Sequence[float]],
    route_distance_miles: float,
    *,
    max_range_miles: float = MAX_RANGE_MILES,
    mpg: float = MPG,
    stations: list[RouteStation] | None = None,
) -> FuelPlan:
    """
    Start with a full tank. Purchase fuel only at selected stops.

    Classic line greedy:
    - While destination is beyond current range, choose among reachable stations.
    - If a cheaper station than current fuel price is in range, go there and fill up.
    - Otherwise fill up at the cheapest reachable station (farthest on a price tie).
    """
    route_points = cumulative_route_miles(coordinates)
    total_miles = route_distance_miles or (route_points[-1][2] if route_points else 0.0)
    if stations is None:
        stations = _candidate_stations(coordinates, route_points)

    if total_miles <= 0:
        return FuelPlan([], 0.0, 0.0, True, notes="Zero-length route")

    tank_gallons = max_range_miles / mpg
    range_left = max_range_miles
    position = 0.0
    current_price: float | None = None
    planned: list[PlannedStop] = []
    purchased_gallons = 0.0
    purchased_cost = 0.0
    seq = 0

    while position + range_left < total_miles - 1e-6:
        reach_end = position + range_left
        candidates = [s for s in stations if position < s.mile_marker <= reach_end]
        if not candidates:
            return FuelPlan(
                planned,
                round(purchased_gallons, 2),
                round(purchased_cost, 2),
                False,
                notes=(
                    "Cannot reach destination: fuel-stop gap exceeds vehicle range"
                ),
            )

        if current_price is not None:
            cheaper = [s for s in candidates if s.price < current_price]
        else:
            cheaper = []

        if cheaper:
            target = min(cheaper, key=lambda s: s.mile_marker)
        else:
            min_price = min(s.price for s in candidates)
            cheapest = [s for s in candidates if abs(s.price - min_price) < 1e-9]
            target = max(cheapest, key=lambda s: s.mile_marker)

        miles_to_target = target.mile_marker - position
        range_left -= miles_to_target
        position = target.mile_marker

        gallons_to_buy = tank_gallons - (range_left / mpg)
        gallons_to_buy = max(0.0, gallons_to_buy)
        if gallons_to_buy > 1e-6:
            cost = gallons_to_buy * target.price
            seq += 1
            planned.append(
                PlannedStop(
                    sequence=seq,
                    stop=target.stop,
                    mile_marker=round(target.mile_marker, 1),
                    price_per_gallon=round(target.price, 4),
                    gallons_to_buy=round(gallons_to_buy, 2),
                    cost=round(cost, 2),
                )
            )
            purchased_gallons += gallons_to_buy
            purchased_cost += cost

        range_left = max_range_miles
        current_price = target.price

    # Short trips (<= one tank): still report a cost-effective on-route stop.
    if not planned and stations and total_miles > 0:
        best = min(stations, key=lambda s: (s.price, s.mile_marker))
        gallons = total_miles / mpg
        cost = gallons * best.price
        planned.append(
            PlannedStop(
                sequence=1,
                stop=best.stop,
                mile_marker=round(best.mile_marker, 1),
                price_per_gallon=round(best.price, 4),
                gallons_to_buy=round(gallons, 2),
                cost=round(cost, 2),
            )
        )
        purchased_gallons = gallons
        purchased_cost = cost
        notes = "Trip within one tank; priced at cheapest station along the route"
    else:
        notes = ""

    return FuelPlan(
        stops=planned,
        total_fuel_gallons=round(purchased_gallons, 2),
        total_fuel_cost=round(purchased_cost, 2),
        reachable=True,
        notes=notes,
    )
