from types import SimpleNamespace
from django.test import SimpleTestCase

from routing.optimizer import RouteStation, plan_fuel_stops


def _stop(opis_id, name, price, lat=0.0, lng=0.0):
    return SimpleNamespace(
        opis_id=opis_id,
        name=name,
        address="addr",
        city="City",
        state="ST",
        lat=lat,
        lng=lng,
        retail_price=price,
    )


class FuelOptimizerTests(SimpleTestCase):
    def test_short_trip_uses_cheapest_on_route(self):
        # Fake geometry ~100 miles eastward (coords unused when stations injected)
        coords = [[0.0, 0.0], [1.5, 0.0]]
        stations = [
            RouteStation(_stop(1, "Expensive", 4.0), mile_marker=20, distance_to_route_miles=1, price=4.0),
            RouteStation(_stop(2, "Cheap", 3.0), mile_marker=40, distance_to_route_miles=1, price=3.0),
        ]
        plan = plan_fuel_stops(coords, route_distance_miles=100.0, stations=stations)
        self.assertTrue(plan.reachable)
        self.assertEqual(len(plan.stops), 1)
        self.assertEqual(plan.stops[0].stop.name, "Cheap")
        self.assertAlmostEqual(plan.total_fuel_gallons, 10.0, places=1)
        self.assertAlmostEqual(plan.total_fuel_cost, 30.0, places=1)

    def test_long_trip_requires_refills(self):
        coords = [[0.0, 0.0], [20.0, 0.0]]
        stations = [
            RouteStation(_stop(1, "A", 3.5), mile_marker=200, distance_to_route_miles=1, price=3.5),
            RouteStation(_stop(2, "B", 3.0), mile_marker=450, distance_to_route_miles=1, price=3.0),
            RouteStation(_stop(3, "C", 3.2), mile_marker=700, distance_to_route_miles=1, price=3.2),
            RouteStation(_stop(4, "D", 2.9), mile_marker=900, distance_to_route_miles=1, price=2.9),
        ]
        plan = plan_fuel_stops(coords, route_distance_miles=1000.0, stations=stations)
        self.assertTrue(plan.reachable)
        self.assertGreaterEqual(len(plan.stops), 1)
        self.assertGreater(plan.total_fuel_cost, 0)
