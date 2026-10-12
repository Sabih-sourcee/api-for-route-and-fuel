"""One-shot smoke test for route planning (no runserver required)."""

import json
import os
import sys
import time

import django

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from routing.services import plan_route  # noqa: E402

start = sys.argv[1] if len(sys.argv) > 1 else "Chicago, IL"
finish = sys.argv[2] if len(sys.argv) > 2 else "Denver, CO"

t0 = time.perf_counter()
result = plan_route(start, finish)
elapsed = time.perf_counter() - t0

summary = {
    "elapsed_seconds": round(elapsed, 2),
    "distance_miles": result["distance_miles"],
    "total_fuel_cost": result["total_fuel_cost"],
    "total_fuel_gallons": result["total_fuel_gallons"],
    "fuel_stop_count": len(result["fuel_stops"]),
    "fuel_stops": [
        {
            "name": s["name"],
            "city": s["city"],
            "state": s["state"],
            "price": s["price_per_gallon"],
            "gallons": s["gallons_to_buy"],
            "cost": s["cost"],
            "mile": s["distance_from_start_miles"],
        }
        for s in result["fuel_stops"]
    ],
    "map_url": result["map_url"],
}
print(json.dumps(summary, indent=2))
