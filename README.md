# Fuel Route API

Django API that plans a USA driving route, picks **cost-effective fuel stops** from the assessment CSV (500 mi range, 10 MPG), and returns a **map URL + route geometry + total fuel cost**.

## Stack

| Piece | Choice |
|-------|--------|
| Framework | Django **5.2.18** + DRF **3.18.3** |
| DB | SQLite (demo) |
| Routing | [OSRM](https://project-osrm.org/) public demo — **1 call / request** |
| Geocoding (start/finish) | [Nominatim](https://nominatim.openstreetmap.org/) (cached) |
| Station coordinates | Offline join to [US Cities Database](https://github.com/kelvins/US-Cities-Database) |

> Django 6.1 is the newest Django line but requires Python ≥ 3.12. This environment has Python 3.11, so **5.2.18 LTS** is used (latest compatible stable).

## Quick start

```powershell
cd C:\Users\PC\Documents\fuel-route-api
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py import_fuel_prices --replace
python manage.py runserver
```

## API

### `POST /api/v1/route/` (also supports `GET`)

```json
{
  "start": "Chicago, IL",
  "finish": "Denver, CO"
}
```

**Example (Postman / curl):**

```powershell
curl -X POST http://127.0.0.1:8000/api/v1/route/ `
  -H "Content-Type: application/json" `
  -d "{\"start\": \"Chicago, IL\", \"finish\": \"Denver, CO\"}"
```

### Response highlights (option C)

- `map_url` — OpenStreetMap directions link (click in Postman)
- `route.geometry` / `route.polyline` — path for maps
- `fuel_stops[]` — ordered optimal fill-ups with price, gallons, cost
- `total_fuel_cost` / `total_fuel_gallons`
- `distance_miles`, `mpg` (10), `max_range_miles` (500)

## Design notes

- Vehicle **starts with a full tank**; purchased fuel is charged at selected stops.
- Stations are filtered to a corridor along the OSRM polyline, then a greedy cost algorithm chooses fills under the 500 mi constraint.
- Geocode + OSRM responses are cached in-memory to keep repeat calls fast and stay polite to free APIs.

## Loom demo checklist

1. Start `runserver`
2. In Postman: `POST /api/v1/route/` with Chicago → Denver
3. Show `fuel_stops`, `total_fuel_cost`, open `map_url`
4. Walk through `routing/services.py`, `routing/optimizer.py`, `stations/management/commands/import_fuel_prices.py`

## Tests

```powershell
python manage.py test routing.tests
```

## Attribution

- Route/geocode: © OpenStreetMap contributors (ODbL), OSRM
- City coordinates: kelvins/US-Cities-Database
- Fuel prices: assessment CSV
