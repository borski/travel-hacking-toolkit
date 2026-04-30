#!/usr/bin/env python3
"""Great-circle distance calculator for multi-segment itineraries.

Used primarily by the round-the-world skill to estimate whether an itinerary
fits under a program's distance cap (Star Alliance RTW: <26k/29k/34k/39k miles;
oneworld Global Explorer: <39k miles; Qantas: <35k miles for cheapest band).

Math: haversine formula for great-circle distance between two lat/lon points.
This is the same formula used by gcmap.com and most airline mileage calculators
(per IATA's Mileage Manual, the "great-circle distance" is the standard).

Airport coordinates come from data/airport-coordinates.json (OpenFlights).

Usage:
    python3 scripts/calc_distance.py SFO LAX
    python3 scripts/calc_distance.py SFO LHR JFK SFO
    python3 scripts/calc_distance.py --json SFO LHR JFK SFO
    echo "SFO LHR JFK SFO" | python3 scripts/calc_distance.py -
"""
import argparse
import json
import math
import sys
from pathlib import Path

EARTH_RADIUS_MILES = 3958.7613  # IATA standard for great-circle calculations


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in statute miles."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_MILES * c


def load_airports() -> dict:
    """Load airport coordinate dictionary from data/airport-coordinates.json."""
    repo_root = Path(__file__).resolve().parent.parent
    data_path = repo_root / "data" / "airport-coordinates.json"
    if not data_path.exists():
        sys.exit(f"FATAL: {data_path} missing. Run from a checkout that includes the data file.")
    with data_path.open() as f:
        return json.load(f)["airports"]


def lookup(airports: dict, code: str) -> dict:
    """Return airport record or exit with helpful error."""
    code = code.upper().strip()
    if code not in airports:
        sys.exit(f"FATAL: IATA code '{code}' not found in airport database.")
    return {"code": code, **airports[code]}


def calculate_segments(codes: list, airports: dict) -> list:
    """Build per-segment + cumulative distance breakdown.

    Returns a list of dicts: [{leg, from, to, distance, cumulative}, ...]
    """
    if len(codes) < 2:
        sys.exit("FATAL: Need at least 2 airport codes (origin + destination).")
    
    segments = []
    cumulative = 0.0
    for i in range(len(codes) - 1):
        a = lookup(airports, codes[i])
        b = lookup(airports, codes[i + 1])
        d = haversine_miles(a["lat"], a["lon"], b["lat"], b["lon"])
        cumulative += d
        segments.append({
            "leg": i + 1,
            "from": a["code"],
            "from_city": a["city"],
            "to": b["code"],
            "to_city": b["city"],
            "distance_miles": round(d),
            "cumulative_miles": round(cumulative),
        })
    return segments


def format_table(segments: list, total: int) -> str:
    """Pretty-print a markdown table of the itinerary."""
    lines = [
        "| Leg | From | To | Segment Miles | Cumulative |",
        "|-----|------|----|--------------:|-----------:|",
    ]
    for s in segments:
        lines.append(
            f"| {s['leg']} | {s['from']} ({s['from_city']}) | "
            f"{s['to']} ({s['to_city']}) | {s['distance_miles']:,} | {s['cumulative_miles']:,} |"
        )
    lines.append("")
    
    # Distance-band annotations
    lines.append(f"**Total: {total:,} miles**")
    lines.append("")
    lines.append("Distance-band lookup:")
    bands = [
        (26000, "Star Alliance RTW Tier 1"),
        (29000, "Star Alliance RTW Tier 2"),
        (34000, "Star Alliance RTW Tier 3"),
        (35000, "Qantas Classic Reward Tier 1 cap"),
        (39000, "Star Alliance RTW Tier 4 / oneworld Global Explorer cap"),
    ]
    for cap, label in bands:
        marker = "OK" if total <= cap else "OVER"
        delta = cap - total
        if delta >= 0:
            lines.append(f"- {label} (≤{cap:,}): **{marker}** ({delta:,} miles to spare)")
        else:
            lines.append(f"- {label} (≤{cap:,}): **{marker}** (over by {-delta:,} miles)")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Great-circle distance for multi-segment flight itineraries."
    )
    parser.add_argument(
        "codes",
        nargs="*",
        help="IATA airport codes in order. e.g. SFO LHR JFK SFO. Use '-' to read from stdin.",
    )
    parser.add_argument("--json", action="store_true", help="JSON output for scripting")
    args = parser.parse_args()

    if args.codes == ["-"]:
        codes = sys.stdin.read().split()
    else:
        codes = args.codes
    
    if not codes:
        parser.print_help()
        sys.exit(2)

    airports = load_airports()
    segments = calculate_segments(codes, airports)
    total = segments[-1]["cumulative_miles"]

    if args.json:
        print(json.dumps({"segments": segments, "total_miles": total}, indent=2))
    else:
        print(format_table(segments, total))


if __name__ == "__main__":
    main()
