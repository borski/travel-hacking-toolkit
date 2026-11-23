#!/usr/bin/env python3
"""Search the local top-1,000 global ski resorts database (data/ski-resorts.json).

Distances are crow-flies (great-circle), NOT driving distance.

Usage:
  python3 skills/ski-resorts/scripts/search_ski_resorts.py --max-crow-flies-mi 60 --hub-only
  python3 skills/ski-resorts/scripts/search_ski_resorts.py --pass dolomiti_superski --country Italy
  python3 skills/ski-resorts/scripts/search_ski_resorts.py --hemisphere south --limit 10
  python3 skills/ski-resorts/scripts/search_ski_resorts.py --query "Zermatt" --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "data" / "ski-resorts.json").exists():
            return parent
    sys.exit("FATAL: data/ski-resorts.json not found. Run scripts/refresh-ski-data.py first.")


def best_airport(resort: dict[str, Any], hub_only: bool) -> dict[str, Any] | None:
    airports = resort.get("nearest_airports", [])
    if hub_only:
        large = [a for a in airports if a.get("type") == "large_airport"]
        if large:
            return large[0]
    return airports[0] if airports else None


def matches(resort: dict[str, Any], args: argparse.Namespace) -> tuple[bool, dict[str, Any] | None]:
    airport = best_airport(resort, args.hub_only)
    if not airport:
        return False, None

    if args.query:
        q = args.query.lower()
        hay = " ".join([
            resort.get("name", ""),
            resort.get("country", ""),
            resort.get("region", ""),
            resort.get("locality", ""),
        ]).lower()
        if q not in hay:
            return False, None

    if args.country:
        if args.country.lower() not in resort.get("country", "").lower():
            return False, None

    if args.region:
        if args.region.lower() not in resort.get("region", "").lower():
            return False, None

    if args.hemisphere and resort.get("hemisphere") != args.hemisphere:
        return False, None

    if args.pass_name:
        target_pass = args.pass_name.lower()
        if target_pass not in [p.lower() for p in resort.get("passes", [])]:
            return False, None

    if args.price_tier and resort.get("price_tier") != args.price_tier:
        return False, None

    if args.max_price_tier:
        order = {"$": 1, "$$": 2, "$$$": 3, "$$$$": 4}
        if order.get(resort.get("price_tier", "$$"), 2) > order.get(args.max_price_tier, 4):
            return False, None

    if args.min_summit_m and resort.get("summit_elevation_m", 0) < args.min_summit_m:
        return False, None

    if args.min_vertical_m and resort.get("vertical_m", 0) < args.min_vertical_m:
        return False, None

    if args.min_lifts and resort.get("lift_count", 0) < args.min_lifts:
        return False, None

    if args.glacier and not resort.get("glacier"):
        return False, None

    if args.max_crow_flies_mi is not None and airport["crow_flies_mi"] > args.max_crow_flies_mi:
        return False, None

    if args.max_crow_flies_km is not None and airport["crow_flies_km"] > args.max_crow_flies_km:
        return False, None

    return True, airport


def format_markdown(results: list[tuple[dict[str, Any], dict[str, Any]]]) -> str:
    if not results:
        return "No matching ski resorts found."
    lines = [
        "| Resort | Country / Region | Nearest Airport (Crow-Flies) | Summit / Vertical | Season | Passes | Price |",
        "|--------|------------------|------------------------------|-------------------|--------|--------|-------|",
    ]
    for r, a in results:
        loc = f"{r['country']}" + (f" ({r['region']})" if r.get("region") else "")
        ap_label = f"{a['iata']} - {a['crow_flies_mi']} mi ({a['crow_flies_km']} km)"
        if a["type"] == "large_airport":
            ap_label += " [Hub]"
        elev = f"{r['summit_elevation_m']}m / {r['vertical_m']}m"
        passes = ", ".join(r["passes"]) if r.get("passes") else "-"
        lines.append(
            f"| {r['name']} | {loc} | {ap_label} | {elev} | {r['typical_season']} | {passes} | {r['price_tier']} |"
        )
    lines.append("")
    lines.append(
        "*Price tier (approx. 1-day adult walk-up lift ticket): "
        "$ <$70 · $$ $70–$120 · $$$ $120–$200 · $$$$ $200+*"
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Search top 1,000 global ski resorts.")
    parser.add_argument("--query", help="Substring match on resort name, country, region, or locality")
    parser.add_argument("--country", help="Filter by country name (e.g., Austria, Japan, United States)")
    parser.add_argument("--region", help="Filter by region/state (e.g., Colorado, Valais, Hokkaido)")
    parser.add_argument("--hemisphere", choices=["north", "south"], help="Filter by hemisphere")
    parser.add_argument("--pass", dest="pass_name", help="Filter by pass (epic, ikon, indy, mountain_collective, dolomiti_superski, superskicard, snow_card_tirol, magic_pass, ski_amade, trois_vallees, portes_du_soleil, mont_blanc_unlimited)")
    parser.add_argument("--price-tier", choices=["$", "$$", "$$$", "$$$$"], help="Exact lift-ticket price tier")
    parser.add_argument("--max-price-tier", choices=["$", "$$", "$$$", "$$$$"], help="Maximum lift-ticket price tier")
    parser.add_argument("--max-crow-flies-mi", type=float, help="Max crow-flies distance to airport in miles")
    parser.add_argument("--max-crow-flies-km", type=float, help="Max crow-flies distance to airport in km")
    parser.add_argument("--hub-only", action="store_true", help="Measure distance to nearest large_airport hub")
    parser.add_argument("--min-summit-m", type=int, default=0, help="Minimum summit elevation in meters")
    parser.add_argument("--min-vertical-m", type=int, default=0, help="Minimum vertical drop in meters")
    parser.add_argument("--min-lifts", type=int, default=0, help="Minimum lift count")
    parser.add_argument("--glacier", action="store_true", help="Only glacier / high-alpine resorts")
    parser.add_argument("--sort", choices=["size", "airport", "summit", "vertical"], default="size", help="Sort order")
    parser.add_argument("--limit", type=int, default=15, help="Max results (default 15)")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of markdown table")
    args = parser.parse_args()

    repo_root = find_repo_root()
    data = json.loads((repo_root / "data" / "ski-resorts.json").read_text(encoding="utf-8"))

    matched: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for r in data["resorts"]:
        ok, ap = matches(r, args)
        if ok and ap is not None:
            matched.append((r, ap))

    if args.sort == "airport":
        matched.sort(key=lambda x: (x[1]["crow_flies_km"], -x[0]["size_score"]))
    elif args.sort == "summit":
        matched.sort(key=lambda x: (-x[0]["summit_elevation_m"], -x[0]["size_score"]))
    elif args.sort == "vertical":
        matched.sort(key=lambda x: (-x[0]["vertical_m"], -x[0]["size_score"]))
    else:
        matched.sort(key=lambda x: -x[0]["size_score"])

    matched = matched[: args.limit]

    if args.json:
        out = [
            {**r, "matched_airport": ap}
            for r, ap in matched
        ]
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(format_markdown(matched))


if __name__ == "__main__":
    main()
