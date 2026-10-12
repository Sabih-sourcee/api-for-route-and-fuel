# Fuel Route API — Design Spec

**Date:** 2026-10-12  
**Status:** Approved for implementation

## Goal

Django API that accepts USA start/finish locations and returns:

1. Route map data (OSM map URL + GeoJSON/polyline)
2. Cost-optimal fuel stops along the route (500 mi max range, 10 MPG)
3. Total fuel spend

## Stack

- Django **5.2.18** (latest compatible with available Python 3.11; Django 6.x needs 3.12+)
- Django REST framework **3.18.3**
- SQLite (demo) / Postgres-ready
- httpx for HTTP clients
- Free APIs: Nominatim (geocode start/finish), OSRM (one route call)
- Station coords: offline match to bundled US cities CSV (no per-request geocode for 8k stations)

## Architecture (modular monolith)

| Module | Responsibility |
|--------|----------------|
| `stations` | FuelStop model, CSV import, city lat/lng join |
| `routing` | Geocoding client, OSRM client, fuel optimizer, API view |

## Assumptions

- Vehicle starts with a **full tank** (500 miles of range)
- Fuel already in the tank at start is not charged; purchases at selected stops are charged
- Gallons purchased cover distance driven after each fill (and remaining distance to destination after last fill)
- Inputs are USA locations (city, state or free-text address)
- Response format **C**: map URL + geometry + structured fuel stops + totals

## External call budget (per request)

1. Nominatim × up to 2 (start, finish) — cached in Django cache
2. OSRM × 1 — route geometry + distance
3. Station data — local DB only

## Fuel optimization algorithm

1. Build route polyline with cumulative distance markers
2. Select stations within corridor (~15 mi of route), project onto route mile marker
3. Deduplicate by opis_id (keep lowest retail price)
4. Greedy optimal fill:
   - While destination not reachable with current range:
     - Consider stations in `(current_pos, current_pos + range]`
     - If a cheaper station than current price exists in range, drive there buying only enough to reach
     - Else drive to cheapest in range and fill to full
   - Track gallons × price for each purchase
5. If trip ≤ 500 mi: optionally stop at cheapest on-route station to price the trip’s gallons (still report that stop)

## API

`POST /api/v1/route/`

```json
{ "start": "Chicago, IL", "finish": "Denver, CO" }
```

Returns option-C JSON (distance, map_url, route geometry, fuel_stops, total_fuel_cost).

## Performance

- Stations preloaded with coordinates at import time
- Geocode + route results cached (TTL ~1 hour)
- Corridor filter uses bounding box then haversine, not N×M over full US without prune
