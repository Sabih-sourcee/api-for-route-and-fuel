"""Import fuel prices CSV and attach lat/lng from US cities database."""

from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from stations.models import FuelStop

STATE_NAME_TO_CODE = {
    "alabama": "AL",
    "alaska": "AK",
    "arizona": "AZ",
    "arkansas": "AR",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "delaware": "DE",
    "district of columbia": "DC",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "iowa": "IA",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "maine": "ME",
    "maryland": "MD",
    "massachusetts": "MA",
    "michigan": "MI",
    "minnesota": "MN",
    "mississippi": "MS",
    "missouri": "MO",
    "montana": "MT",
    "nebraska": "NE",
    "nevada": "NV",
    "new hampshire": "NH",
    "new jersey": "NJ",
    "new mexico": "NM",
    "new york": "NY",
    "north carolina": "NC",
    "north dakota": "ND",
    "ohio": "OH",
    "oklahoma": "OK",
    "oregon": "OR",
    "pennsylvania": "PA",
    "rhode island": "RI",
    "south carolina": "SC",
    "south dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "vermont": "VT",
    "virginia": "VA",
    "washington": "WA",
    "west virginia": "WV",
    "wisconsin": "WI",
    "wyoming": "WY",
    "puerto rico": "PR",
}


def _norm_city(value: str) -> str:
    return " ".join(value.strip().lower().split())


def load_city_coords(cities_path: Path) -> dict[tuple[str, str], tuple[float, float]]:
    """Map (city_norm, state_code) -> (lat, lng). Prefer first occurrence."""
    coords: dict[tuple[str, str], tuple[float, float]] = {}
    with cities_path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            city = _norm_city(row.get("CITY") or row.get("city") or "")
            state_raw = (row.get("STATE_CODE") or row.get("state_code") or "").strip()
            if not state_raw:
                state_name = (row.get("STATE_NAME") or row.get("state_name") or "").strip().lower()
                state_raw = STATE_NAME_TO_CODE.get(state_name, "")
            state = state_raw.upper()
            if not city or not state:
                continue
            try:
                lat = float(row.get("LATITUDE") or row.get("lat") or "")
                lng = float(row.get("LONGITUDE") or row.get("lng") or "")
            except (TypeError, ValueError):
                continue
            key = (city, state)
            if key not in coords:
                coords[key] = (lat, lng)
    return coords


class Command(BaseCommand):
    help = "Import fuel price CSV and geocode via bundled US cities file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            default=str(settings.BASE_DIR / "data" / "fuel-prices.csv"),
            help="Path to fuel prices CSV",
        )
        parser.add_argument(
            "--cities",
            default=str(settings.BASE_DIR / "data" / "us_cities.csv"),
            help="Path to US cities CSV with lat/lng",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Delete existing FuelStop rows before import",
        )

    def handle(self, *args, **options):
        fuel_path = Path(options["csv"])
        cities_path = Path(options["cities"])
        if not fuel_path.exists():
            self.stderr.write(f"Fuel CSV not found: {fuel_path}")
            return
        if not cities_path.exists():
            self.stderr.write(f"Cities CSV not found: {cities_path}")
            return

        self.stdout.write("Loading city coordinates...")
        city_coords = load_city_coords(cities_path)
        self.stdout.write(f"Loaded {len(city_coords)} city/state coordinates")

        if options["replace"]:
            deleted, _ = FuelStop.objects.all().delete()
            self.stdout.write(f"Deleted {deleted} existing rows")

        created = 0
        matched = 0
        unmatched = 0
        batch: list[FuelStop] = []

        with fuel_path.open(encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                try:
                    opis_id = int(row["OPIS Truckstop ID"])
                except (KeyError, ValueError):
                    continue
                try:
                    price = Decimal(str(row["Retail Price"]).strip())
                except (InvalidOperation, KeyError):
                    continue

                city = (row.get("City") or "").strip()
                state = (row.get("State") or "").strip().upper()
                lat = lng = None
                coords = city_coords.get((_norm_city(city), state))
                if coords:
                    lat, lng = coords
                    matched += 1
                else:
                    unmatched += 1

                rack_raw = (row.get("Rack ID") or "").strip()
                rack_id = int(rack_raw) if rack_raw.isdigit() else None

                batch.append(
                    FuelStop(
                        opis_id=opis_id,
                        name=(row.get("Truckstop Name") or "").strip()[:255],
                        address=(row.get("Address") or "").strip()[:255],
                        city=city[:128],
                        state=state[:8],
                        rack_id=rack_id,
                        retail_price=price,
                        lat=lat,
                        lng=lng,
                    )
                )
                if len(batch) >= 1000:
                    with transaction.atomic():
                        FuelStop.objects.bulk_create(batch, batch_size=1000)
                    created += len(batch)
                    batch.clear()

        if batch:
            with transaction.atomic():
                FuelStop.objects.bulk_create(batch, batch_size=1000)
            created += len(batch)

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {created} stations "
                f"(geocoded {matched}, unmatched city {unmatched})"
            )
        )
