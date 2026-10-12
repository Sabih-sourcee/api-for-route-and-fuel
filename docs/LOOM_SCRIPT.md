# Loom script (≤ 5 minutes)

Record in Loom with: terminal (server running) + Postman + VS Code/Cursor.

## Before you hit Record

```bat
cd C:\Users\PC\Documents\fuel-route-api
.\.venv\Scripts\activate.bat
python manage.py runserver
```

Import Postman collection: `postman/Fuel_Route_API.postman_collection.json`

---

## 0:00–0:30 — Intro

> “This is a Django API that takes USA start and finish locations, returns a driving route map, cost-optimal fuel stops from the assessment CSV, and total fuel cost. Vehicle range is 500 miles at 10 MPG.”

Show: `README.md` briefly.

## 0:30–2:00 — Postman demo (most important)

1. Open Postman → **Plan route (POST) — Chicago to Denver**
2. Hit **Send**
3. Point out in the JSON response:
   - `distance_miles`
   - `map_url` → click/open it (OSM map)
   - `fuel_stops` (multiple stops, prices, gallons, cost)
   - `total_fuel_cost` / `total_fuel_gallons`
4. Optional: send a second request (NYC→Boston) to show speed / cache

Say:

> “Routing uses one OSRM call per request. Start/finish geocoding uses Nominatim and is cached. Fuel prices come from the local database, not live map APIs.”

## 2:00–4:00 — Code overview

| File | What to say |
|------|-------------|
| `routing/views.py` | API endpoint `POST/GET /api/v1/route/` |
| `routing/services.py` | Orchestrates geocode → **1× OSRM** → fuel plan → JSON |
| `routing/optimizer.py` | Greedy cost-optimal fills under 500 mi / 10 MPG |
| `routing/clients.py` | Free OSRM + Nominatim clients |
| `stations/models.py` | FuelStop model |
| `stations/management/commands/import_fuel_prices.py` | CSV import + city lat/lng join |

## 4:00–4:45 — Requirements checklist

> “Django latest stable compatible with this Python (5.2.18 LTS). Fast responses via preloaded stations and caching. Ideally one routing API call. GitHub link is in the description.”

## 4:45–5:00 — Close

> “Thanks — happy to answer questions.”

Paste GitHub URL in the Loom description after you push.
