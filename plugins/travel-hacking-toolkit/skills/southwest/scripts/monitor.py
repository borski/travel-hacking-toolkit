#!/usr/bin/env python3
"""Monitor Southwest fares against known reservation baselines.

Reads a JSON config of booked trips (route, dates, paid baseline per leg) and
runs search_fares for each leg. Reports any leg where current cheapest Basic
fare in points has dropped below the paid baseline.

This is the right tool for Companion Pass-linked reservations, where the
change-flight flow on southwest.com is blocked. It works for any reservation
since it just queries public fare search, no login needed.

Config format (JSON):
    [
      {
        "name": "Trip label (display only)",
        "confirmation": "ABC123",
        "passenger": "Free-text label (display only)",
        "outbound": {
          "origin": "SJC",
          "dest": "DEN",
          "date": "2026-12-15",
          "flight_number": "1234",
          "baseline_pts": 10000
        },
        "return": {
          "origin": "DEN",
          "dest": "SJC",
          "date": "2026-12-20",
          "flight_number": "5678 / 9012",
          "baseline_pts": 12000
        }
      }
    ]

flight_number must match exactly how SW displays it in search results,
including spaces around `/` for multi-segment flights. The `return` leg
can be omitted for one-way trips.

Usage:
    python3 monitor.py --config trips.json [--json] [--only CONF]
    cat trips.json | python3 monitor.py --config - [--json]
"""

import argparse
import json
import re
import sys
import tempfile
import shutil
from pathlib import Path
from patchright.sync_api import sync_playwright

# Reuse the search_fares logic
sys.path.insert(0, str(Path(__file__).parent))
from search_fares import (
    fetch_flights,
    HOMEPAGE,
)


def log(msg):
    print(f"[sw-monitor] {msg}", file=sys.stderr)


def parse_basic_pts(flight):
    """Parse the Basic fare in points from a flight dict.

    Each fare value looks like "23,500 pts +$5.60". Returns int points
    or None if no parseable Basic fare.
    """
    basic = flight.get("fares", {}).get("Basic", "")
    m = re.match(r"([\d,]+)\s*pts", basic)
    if not m:
        return None
    return int(m.group(1).replace(",", ""))


def cheapest_basic_pts(flights):
    """Return cheapest Basic fare across all flights as (points, flight)."""
    cheapest_pts = None
    cheapest_flight = None
    for f in flights:
        pts = parse_basic_pts(f)
        if pts is None:
            continue
        if cheapest_pts is None or pts < cheapest_pts:
            cheapest_pts = pts
            cheapest_flight = f
    return cheapest_pts, cheapest_flight


def find_specific_flight(flights, flight_number):
    """Find the specific booked flight in the search results.

    SW shows flight numbers like '4107' or '3657 / 4630' (multi-segment).
    Match exactly on the displayed flight_number string.
    """
    if not flight_number:
        return None
    target = flight_number.replace(" ", "")
    for f in flights:
        actual = (f.get("flight_number") or "").replace(" ", "")
        if actual == target:
            return f
    return None


def check_leg(page, leg, label):
    """Search SW for one leg and compare cheapest fare to baseline.

    Returns dict with current/baseline/savings/flight info.

    Navigates to the SW homepage between every search. SW's SPA caches
    state heavily; without a homepage hop, the second search-results URL
    often shows nothing because React doesn't re-render. Going home
    between searches forces a clean state.
    """
    log(f"  {label}: {leg['origin']} -> {leg['dest']} on {leg['date']}...")

    # SW SPA + slow network → empty results sometimes. Retry once on empty.
    # Also: SW caches state. Force a real navigation reset before each search,
    # and verify the results page reflects THIS request (not a stale prior one).
    flights = []
    for attempt in (1, 2, 3):
        # Hard reset: navigate to about:blank then homepage
        try:
            page.goto("about:blank", timeout=10000)
            page.wait_for_timeout(500)
        except Exception:
            pass
        page.goto(HOMEPAGE, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2500)

        flights = fetch_flights(
            page,
            leg["origin"],
            leg["dest"],
            leg["date"],
            return_date=None,
            fare_type="POINTS",
        )

        # Validate: results URL must contain THIS leg's origin/dest, otherwise
        # we got a stale render. Discard.
        url = page.url
        url_origin_ok = leg["origin"] in url
        url_dest_ok = leg["dest"] in url
        if flights and url_origin_ok and url_dest_ok:
            break
        if flights and not (url_origin_ok and url_dest_ok):
            log(
                f"    attempt {attempt}: stale results (URL: {url[:120]}), "
                f"discarding {len(flights)} flights"
            )
            flights = []
        else:
            log(f"    attempt {attempt}: no flights, retrying...")
        page.wait_for_timeout(3000)

    if not flights:
        return {
            "label": label,
            "origin": leg["origin"],
            "dest": leg["dest"],
            "date": leg["date"],
            "baseline_pts": leg.get("baseline_pts"),
            "current_pts": None,
            "savings_pts": None,
            "status": "no_flights_found",
            "flight_count": 0,
        }

    baseline = leg.get("baseline_pts")
    target_flight_num = leg.get("flight_number")

    # Look for the SPECIFIC booked flight first
    booked = find_specific_flight(flights, target_flight_num)
    if booked is None and target_flight_num:
        return {
            "label": label,
            "origin": leg["origin"],
            "dest": leg["dest"],
            "date": leg["date"],
            "baseline_pts": baseline,
            "current_pts": None,
            "savings_pts": None,
            "status": "booked_flight_not_in_results",
            "flight_count": len(flights),
            "target_flight_number": target_flight_num,
        }

    booked_pts = parse_basic_pts(booked) if booked else None

    if booked_pts is None:
        return {
            "label": label,
            "origin": leg["origin"],
            "dest": leg["dest"],
            "date": leg["date"],
            "baseline_pts": baseline,
            "current_pts": None,
            "savings_pts": None,
            "status": "no_basic_fare_for_booked_flight",
            "flight_count": len(flights),
            "target_flight_number": target_flight_num,
        }

    savings = (baseline - booked_pts) if baseline is not None else None
    status = "savings" if (savings is not None and savings > 0) else "no_change"

    return {
        "label": label,
        "origin": leg["origin"],
        "dest": leg["dest"],
        "date": leg["date"],
        "baseline_pts": baseline,
        "current_pts": booked_pts,
        "savings_pts": savings,
        "status": status,
        "flight_count": len(flights),
        "booked_flight": {
            "flight_number": booked.get("flight_number"),
            "depart_time": booked.get("depart_time"),
            "arrive_time": booked.get("arrive_time"),
            "stops": booked.get("stops"),
            "duration": booked.get("duration"),
        },
    }


def monitor_trips(config, only_conf=None):
    """Run check on every leg of every trip in config."""
    tmpdir = tempfile.mkdtemp(prefix="sw_monitor_")
    results = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                tmpdir,
                headless=False,
                viewport={"width": 1440, "height": 900},
                locale="en-US",
                timezone_id="America/Los_Angeles",
            )
            page = browser.new_page()
            page.goto(HOMEPAGE, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)

            for trip in config:
                if only_conf and trip.get("confirmation") != only_conf:
                    continue
                log(
                    f"Checking {trip.get('name', '?')} "
                    f"({trip.get('confirmation', '?')})..."
                )
                trip_result = {
                    "name": trip.get("name"),
                    "confirmation": trip.get("confirmation"),
                    "legs": [],
                }
                for leg_key in ["outbound", "return"]:
                    if leg_key in trip and trip[leg_key]:
                        leg_result = check_leg(page, trip[leg_key], leg_key)
                        trip_result["legs"].append(leg_result)

                # Trip-level summary
                total_savings = sum(
                    l["savings_pts"]
                    for l in trip_result["legs"]
                    if l.get("savings_pts") and l["savings_pts"] > 0
                )
                trip_result["total_savings_pts"] = total_savings
                trip_result["has_savings"] = total_savings > 0
                results.append(trip_result)

            browser.close()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    return results


def print_results(results):
    """Pretty-print monitor results."""
    print("\nSouthwest Fare Monitor Results")
    print("=" * 70)
    any_savings = False

    for trip in results:
        name = trip.get("name", "?")
        conf = trip.get("confirmation", "?")
        savings = trip.get("total_savings_pts", 0)
        marker = "*** SAVINGS ***" if savings > 0 else ""
        print(f"\n{name}  ({conf})  {marker}")
        print("-" * 70)

        for leg in trip["legs"]:
            label = leg["label"]
            route = f"{leg['origin']} -> {leg['dest']}"
            date = leg["date"]
            baseline = leg.get("baseline_pts")
            current = leg.get("current_pts")
            leg_savings = leg.get("savings_pts")
            status = leg.get("status", "?")

            base_str = f"{baseline:,} pts" if baseline is not None else "(no baseline)"
            curr_str = f"{current:,} pts" if current is not None else f"({status})"

            if leg_savings is not None and leg_savings > 0:
                save_str = f"SAVES {leg_savings:,} pts"
                any_savings = True
            elif leg_savings is not None and leg_savings < 0:
                save_str = f"+{abs(leg_savings):,} pts (more expensive now)"
            else:
                save_str = ""

            print(
                f"  {label:<10} {route:<14} {date}   "
                f"baseline {base_str:<14} -> now {curr_str:<14} {save_str}"
            )

            booked = leg.get("booked_flight") or {}
            if booked.get("flight_number"):
                print(
                    f"             booked: #{booked['flight_number']} "
                    f"{booked.get('depart_time', '?')}-{booked.get('arrive_time', '?')} "
                    f"({booked.get('stops', '?')}, {booked.get('duration', '?')})"
                )
            elif leg.get("status") == "booked_flight_not_in_results":
                print(
                    f"             ! booked flight #{leg.get('target_flight_number')} "
                    f"not found in current SW results (schedule changed?)"
                )

        if savings > 0:
            print(f"  >> Trip total: SAVE {savings:,} points if rebooked")

    print("\n" + "=" * 70)
    if any_savings:
        print("REBOOK OPPORTUNITIES FOUND. Review above.")
    else:
        print("No savings found. All current prices >= what was paid.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Monitor SW fares against booked baselines"
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to trips JSON config (or '-' for stdin)",
    )
    parser.add_argument(
        "--only", help="Only check the trip with this confirmation number"
    )
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    if args.config == "-":
        config = json.load(sys.stdin)
    else:
        with open(args.config) as f:
            config = json.load(f)

    if not isinstance(config, list):
        log("ERROR: config must be a JSON array of trip objects")
        sys.exit(1)

    results = monitor_trips(config, only_conf=args.only)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_results(results)
