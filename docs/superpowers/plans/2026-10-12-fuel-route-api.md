# Fuel Route API Implementation Plan

> **For agentic workers:** Implement task-by-task.

**Goal:** Django API returning USA route map + cost-optimal fuel stops + total fuel cost.

**Architecture:** Modular monolith — `stations` (CSV/geo) + `routing` (OSRM/Nominatim/optimizer/API).

**Tech Stack:** Django 5.2.18, DRF 3.18.3, httpx, SQLite, OSRM, Nominatim.

## Global Constraints

- Max 1–3 map/routing API calls per request (ideal: 1 OSRM)
- Vehicle range 500 mi, 10 MPG, start full tank
- Response format C (map URL + geometry + stops)
- Fast responses via preloaded station coords + caching

## Tasks

- [x] Scaffold Django project + apps
- [x] FuelStop model + import_fuel_prices command
- [x] Geo helpers, Nominatim + OSRM clients
- [x] Fuel optimizer + route service + API view
- [x] README + optimizer unit tests
- [ ] migrate + import CSV + smoke-test live API
