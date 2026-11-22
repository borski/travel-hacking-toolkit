#!/usr/bin/env python3
"""Fetch current snow depth and 7-14 day weather/snowfall forecast via Open-Meteo.

Free, open-source API (no key required, non-commercial use).

Usage:
  python3 skills/ski-resorts/scripts/fetch_snow.py --resorts "Zermatt,Mammoth Mountain,Niseko"
  python3 skills/ski-resorts/scripts/fetch_snow.py --resorts "Alta,Snowbird" --days 14 --json
  python3 skills/ski-resorts/scripts/fetch_snow.py --lat 46.0207 --lon 7.7491 --name "Zermatt"
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def find_repo_root() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "data" / "ski-resorts.json").exists():
            return parent
    return None


def resolve_resorts(names: list[str]) -> list[dict[str, Any]]:
    root = find_repo_root()
    if root is None:
        sys.exit("FATAL: data/ski-resorts.json not found.")
    data = json.loads((root / "data" / "ski-resorts.json").read_text(encoding="utf-8"))
    resolved = []
    for raw in names:
        q = raw.strip().lower()
        if not q:
            continue
        exact = [r for r in data["resorts"] if r["name"].lower() == q]
        matches = exact or [r for r in data["resorts"] if q in r["name"].lower()]
        if matches:
            resolved.append(matches[0])
        else:
            print(f"WARN: Resort '{raw}' not found in top 1,000 database.", file=sys.stderr)
    return resolved


def fetch_forecast(lat: float, lon: float, days: int) -> dict[str, Any]:
    params = urllib.parse.urlencode({
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "current": "temperature_2m,snow_depth,snowfall",
        "daily": "snowfall_sum,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "forecast_days": str(min(max(days, 1), 16)),
        "timezone": "auto",
    })
    url = f"{OPEN_METEO_URL}?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "travel-hacking-toolkit/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def summarize(
    name: str,
    country: str,
    lat: float,
    lon: float,
    days: int,
    nearest_airports: list[dict[str, Any]] | None = None,
    min_snow_cm: float | None = None,
) -> dict[str, Any]:
    raw = fetch_forecast(lat, lon, days)
    cur = raw.get("current", {})
    daily = raw.get("daily", {})
    snow_vals = [v or 0.0 for v in daily.get("snowfall_sum", [])]
    tmax_vals = [v for v in daily.get("temperature_2m_max", []) if v is not None]
    tmin_vals = [v for v in daily.get("temperature_2m_min", []) if v is not None]

    # Open-Meteo current.snow_depth is in meters; convert to cm for readability
    cur_depth_m = cur.get("snow_depth")
    cur_depth_cm = round(cur_depth_m * 100) if cur_depth_m is not None else None
    total_cm = round(sum(snow_vals), 1)

    out: dict[str, Any] = {
        "name": name,
        "country": country,
        "lat": lat,
        "lon": lon,
        "current_temp_c": cur.get("temperature_2m"),
        "current_snow_depth_cm": cur_depth_cm,
        "forecast_days": len(snow_vals),
        "snowfall_7d_cm": round(sum(snow_vals[:7]), 1),
        "snowfall_total_cm": total_cm,
        "temp_min_c": min(tmin_vals) if tmin_vals else None,
        "temp_max_c": max(tmax_vals) if tmax_vals else None,
    }
    if nearest_airports is not None:
        out["nearest_airports"] = nearest_airports
    if min_snow_cm is not None:
        out["alert"] = total_cm >= min_snow_cm
    return out


def format_markdown(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No resorts met the snow threshold."
    days = rows[0]["forecast_days"]
    has_alerts = any("alert" in r for r in rows)
    header = f"| Resort | Current Depth | Current Temp | 7d Snowfall | {days}d Snowfall | {days}d Temp Range | Nearest Airport (Crow-Flies) |"
    sep = "|--------|--------------:|-------------:|------------:|-------------:|-----------------|------------------------------|"
    if has_alerts:
        header += " Alert |"
        sep += "-------|"
    lines = [header, sep]
    for r in rows:
        depth = f"{r['current_snow_depth_cm']} cm" if r["current_snow_depth_cm"] is not None else "n/a"
        ctemp = f"{r['current_temp_c']}°C" if r["current_temp_c"] is not None else "n/a"
        trange = (
            f"{r['temp_min_c']}°C to {r['temp_max_c']}°C"
            if r["temp_min_c"] is not None and r["temp_max_c"] is not None
            else "n/a"
        )
        aps = r.get("nearest_airports") or []
        ap_str = f"{aps[0]['iata']} ({aps[0]['crow_flies_mi']} mi)" if aps else "-"
        row = f"| {r['name']} | {depth} | {ctemp} | {r['snowfall_7d_cm']} cm | {r['snowfall_total_cm']} cm | {trange} | {ap_str} |"
        if has_alerts:
            row += f" {'SNOW DUMP' if r.get('alert') else '-'} |"
        lines.append(row)
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch live snow depth & 1-2 week forecast via Open-Meteo.")
    parser.add_argument("--resorts", help="Comma-separated resort names from data/ski-resorts.json")
    parser.add_argument("--lat", type=float, help="Manual latitude (use with --lon)")
    parser.add_argument("--lon", type=float, help="Manual longitude (use with --lat)")
    parser.add_argument("--name", default="Custom Location", help="Label for manual --lat/--lon")
    parser.add_argument("--days", type=int, default=14, help="Forecast days (1-16, default 14)")
    parser.add_argument("--min-snow-cm", type=float, help="Flag resorts with >= N cm forecast snowfall (powder alert)")
    parser.add_argument("--alerts-only", action="store_true", help="Only output resorts meeting --min-snow-cm")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    targets: list[tuple[str, str, float, float, list[dict[str, Any]] | None]] = []
    if args.resorts:
        for r in resolve_resorts(args.resorts.split(",")):
            targets.append((r["name"], r["country"], r["lat"], r["lon"], r.get("nearest_airports", [])))
    elif args.lat is not None and args.lon is not None:
        targets.append((args.name, "", args.lat, args.lon, None))
    else:
        sys.exit("Provide --resorts 'Name1,Name2' or --lat X --lon Y.")

    results = [
        summarize(name, country, lat, lon, args.days, aps, args.min_snow_cm)
        for name, country, lat, lon, aps in targets
    ]
    if args.alerts_only and args.min_snow_cm is not None:
        results = [r for r in results if r.get("alert")]

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(format_markdown(results))


if __name__ == "__main__":
    main()
