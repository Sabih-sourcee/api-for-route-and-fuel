"""
Record a short demo video (webm) of the Fuel Route API for Loom upload.

Produces: demo/fuel-route-demo.webm
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import django
import httpx
from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from routing.services import plan_route  # noqa: E402

OUT_DIR = BASE / "demo"
OUT_DIR.mkdir(exist_ok=True)


def build_demo_html(payload: dict) -> Path:
    stops_rows = "".join(
        f"<tr><td>{s['sequence']}</td><td>{s['name']}</td>"
        f"<td>{s['city']}, {s['state']}</td><td>${s['price_per_gallon']:.3f}</td>"
        f"<td>{s['gallons_to_buy']}</td><td>${s['cost']:.2f}</td>"
        f"<td>{s['distance_from_start_miles']} mi</td></tr>"
        for s in payload["fuel_stops"]
    )
    pretty = json.dumps(
        {
            "distance_miles": payload["distance_miles"],
            "total_fuel_cost": payload["total_fuel_cost"],
            "total_fuel_gallons": payload["total_fuel_gallons"],
            "mpg": payload["mpg"],
            "max_range_miles": payload["max_range_miles"],
            "map_url": payload["map_url"],
            "fuel_stops": payload["fuel_stops"],
        },
        indent=2,
    )
    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Fuel Route API Demo</title>
  <style>
    body {{ font-family: Segoe UI, sans-serif; margin: 0; background: #0f172a; color: #e2e8f0; }}
    header {{ padding: 28px 40px; background: #020617; border-bottom: 1px solid #1e293b; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; }}
    .sub {{ color: #94a3b8; }}
    main {{ display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 24px; padding: 28px 40px; }}
    .card {{ background: #111827; border: 1px solid #1f2937; border-radius: 14px; padding: 20px; }}
    .label {{ font-size: 12px; text-transform: uppercase; letter-spacing: .08em; color: #64748b; }}
    .req {{ font-family: Consolas, monospace; background: #020617; padding: 14px; border-radius: 10px; margin-top: 10px; }}
    .method {{ color: #34d399; font-weight: 700; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 14px; }}
    th, td {{ text-align: left; padding: 8px 6px; border-bottom: 1px solid #1f2937; }}
    th {{ color: #93c5fd; }}
    .stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 14px; }}
    .stat {{ background: #020617; border-radius: 10px; padding: 14px; }}
    .stat b {{ display: block; font-size: 22px; margin-top: 6px; color: #f8fafc; }}
    pre {{ white-space: pre-wrap; word-break: break-word; font-size: 12px; max-height: 420px; overflow: auto; background: #020617; padding: 14px; border-radius: 10px; }}
    .code {{ font-family: Consolas, monospace; font-size: 13px; line-height: 1.45; }}
    a {{ color: #38bdf8; }}
    .slide {{ display: none; }}
    .slide.active {{ display: block; }}
  </style>
</head>
<body>
  <header>
    <h1>Fuel Route API — Demo</h1>
    <div class="sub">Django + OSRM (1 route call) + cost-optimal fuel stops · 500 mi range · 10 MPG</div>
  </header>
  <main>
    <section class="card slide active" id="slide-api">
      <div class="label">Postman-style request</div>
      <div class="req"><span class="method">POST</span> http://127.0.0.1:8000/api/v1/route/</div>
      <div class="req">{{"start": "Chicago, IL", "finish": "Denver, CO"}}</div>
      <div class="stats">
        <div class="stat"><div class="label">Distance</div><b>{payload['distance_miles']} mi</b></div>
        <div class="stat"><div class="label">Fuel cost</div><b>${payload['total_fuel_cost']:.2f}</b></div>
        <div class="stat"><div class="label">Stops</div><b>{len(payload['fuel_stops'])}</b></div>
      </div>
      <div class="label" style="margin-top:18px">Optimal fuel stops</div>
      <table>
        <thead><tr><th>#</th><th>Name</th><th>Location</th><th>$/gal</th><th>Gal</th><th>Cost</th><th>Mile</th></tr></thead>
        <tbody>{stops_rows}</tbody>
      </table>
      <p style="margin-top:16px"><a id="maplink" href="{payload['map_url']}" target="_blank">Open route map (OpenStreetMap / OSRM)</a></p>
    </section>
    <section class="card slide active" id="slide-json">
      <div class="label">API JSON response (highlights)</div>
      <pre id="json">{pretty}</pre>
    </section>
    <section class="card slide" id="slide-code" style="grid-column: 1 / -1">
      <div class="label">Code overview</div>
      <div class="code">
routing/views.py      → POST/GET /api/v1/route/<br/>
routing/services.py   → geocode start/finish → <b>1× OSRM route</b> → fuel plan → JSON<br/>
routing/clients.py    → free Nominatim + OSRM (cached)<br/>
routing/optimizer.py  → greedy cost-optimal fills (500 mi / 10 MPG)<br/>
stations/models.py    → FuelStop from assessment CSV<br/>
stations/.../import_fuel_prices.py → offline city lat/lng join (fast, no live geocode per station)
      </div>
    </section>
  </main>
  <script>
    // Used by the recorder to flip slides via page.evaluate
    window.showCode = () => {{
      document.getElementById('slide-api').classList.remove('active');
      document.getElementById('slide-json').classList.remove('active');
      document.getElementById('slide-code').classList.add('active');
      document.getElementById('slide-code').style.display = 'block';
    }};
  </script>
</body>
</html>"""
    path = OUT_DIR / "demo.html"
    path.write_text(html, encoding="utf-8")
    return path


def main() -> None:
    print("Planning Chicago -> Denver...")
    payload = plan_route("Chicago, IL", "Denver, CO")
    html_path = build_demo_html(payload)
    print(f"Wrote {html_path}")

    video_dir = OUT_DIR / "video_raw"
    video_dir.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            record_video_dir=str(video_dir),
            record_video_size={"width": 1440, "height": 900},
        )
        page = context.new_page()

        # Title beat
        page.set_content(
            "<html><body style='margin:0;background:#020617;color:white;"
            "font-family:Segoe UI;display:flex;align-items:center;justify-content:center;"
            "height:100vh'><div style='text-align:center'><h1>Fuel Route API</h1>"
            "<p>Django · OSRM · Cost-optimal fuel stops</p></div></body></html>"
        )
        page.wait_for_timeout(2500)

        page.goto(html_path.as_uri())
        page.wait_for_timeout(4000)
        page.evaluate("window.scrollTo(0, 200)")
        page.wait_for_timeout(2500)

        # Open map
        with context.expect_page() as new_page_info:
            page.click("#maplink")
        map_page = new_page_info.value
        map_page.wait_for_load_state("domcontentloaded")
        map_page.wait_for_timeout(4500)
        map_page.close()

        page.bring_to_front()
        page.evaluate("window.showCode()")
        page.wait_for_timeout(4500)

        page.set_content(
            "<html><body style='margin:0;background:#020617;color:#e2e8f0;"
            "font-family:Segoe UI;display:flex;align-items:center;justify-content:center;"
            "height:100vh'><div style='max-width:800px'>"
            "<h2>Requirements covered</h2>"
            "<ul style='font-size:20px;line-height:1.7'>"
            "<li>Django API · USA start/finish</li>"
            "<li>Map URL + route geometry + fuel stops + total cost</li>"
            "<li>500 mi range · 10 MPG · assessment CSV prices</li>"
            "<li>One OSRM routing call per request (geocode cached)</li>"
            "</ul></div></body></html>"
        )
        page.wait_for_timeout(3500)

        page.close()
        context.close()
        browser.close()

    videos = list(video_dir.glob("*.webm"))
    if not videos:
        raise SystemExit("No video produced")
    final = OUT_DIR / "fuel-route-demo.webm"
    videos[0].replace(final)
    print(f"DONE: {final}")
    print(f"Size: {final.stat().st_size / 1_000_000:.1f} MB")
    print("Upload this file to Loom (New video → Upload), or screen-record while playing it.")


if __name__ == "__main__":
    main()
