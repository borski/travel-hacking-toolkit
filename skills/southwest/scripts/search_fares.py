#!/usr/bin/env python3
"""Search Southwest for flight fares using Patchright (undetected Playwright).

Requires: pip install patchright && patchright install chromium
Note: MUST run in headed mode (headless=False). SW blocks headless browsers.
A Chrome window will briefly appear and close.

Usage:
    python3 search_fares.py --origin SJC --dest DEN --depart 2026-05-15 [--return 2026-05-18] [--points] [--json]
"""

import argparse
import json
import re
import sys
import tempfile
import shutil
from patchright.sync_api import sync_playwright


RESULTS_URL = "https://www.southwest.com/air/booking/select.html"
HOMEPAGE = "https://www.southwest.com"
WAIT_FOR_RESULTS = 15  # seconds to wait for results to render
FARE_NAMES = ["Basic", "Choice", "Choice Preferred", "Choice Extra"]


def build_url(origin, dest, depart, return_date=None, fare_type="USD"):
    """Build the SW results page URL. Use fareType=POINTS for points pricing."""
    params = {
        "adultPassengersCount": "1",
        "departureDate": depart,
        "departureTimeOfDay": "ALL_DAY",
        "destinationAirportCode": dest,
        "fareType": fare_type,
        "originationAirportCode": origin,
        "passengerType": "ADULT",
        "returnDate": return_date or "",
        "returnTimeOfDay": "ALL_DAY",
        "tripType": "roundtrip" if return_date else "oneway",
    }
    return RESULTS_URL + "?" + "&".join(f"{k}={v}" for k, v in params.items())


def parse_flight_block(text):
    """Parse a single flight block into structured data."""
    flight = {}

    # Flight number
    m = re.search(r"# ([\d/ ]+)", text)
    if m:
        flight["flight_number"] = m.group(1).strip()

    # Times
    times = re.findall(r"(\d{1,2}:\d{2}(?:AM|PM))", text)
    if len(times) >= 2:
        flight["depart_time"] = times[0]
        flight["arrive_time"] = times[1]

    # Stops and connection
    if "Nonstop" in text:
        flight["stops"] = "Nonstop"
    else:
        sm = re.search(r"(\d+)\s*stop", text, re.I)
        flight["stops"] = f"{sm.group(1)} stop" if sm else "?"
        conn = re.search(r"Change planes\s+(\w+)", text)
        if conn:
            flight["connection"] = conn.group(1)

    # Duration
    m = re.search(r"(\d+h\s*\d+m)", text)
    if m:
        flight["duration"] = m.group(1)

    # Points fares: "23,500 Points"
    point_fares = re.findall(r"([\d,]+)\s*Points", text)
    if point_fares:
        tax = re.search(r"\+\$(\d+\.\d+)", text)
        tax_str = f" +${tax.group(1)}" if tax else ""
        flight["fares"] = {}
        for i, pts in enumerate(point_fares):
            name = FARE_NAMES[i] if i < len(FARE_NAMES) else f"Fare {i + 1}"
            flight["fares"][name] = f"{pts} pts{tax_str}"
        flight["fare_type"] = "points"
        return flight

    # Cash fares: "277 Dollars" or "Unavailable"
    fare_entries = re.findall(r"(?:Unavailable|(\d+) Dollars)", text)
    if fare_entries:
        flight["fares"] = {}
        for i, fare in enumerate(fare_entries):
            name = FARE_NAMES[i] if i < len(FARE_NAMES) else f"Fare {i + 1}"
            flight["fares"][name] = f"${fare}" if fare else "Unavail"
        flight["fare_type"] = "cash"

    # Seats left warnings
    left = re.findall(r"(\d+) left", text)
    if left:
        flight["low_inventory"] = True

    return flight


def fetch_flights(page, origin, dest, depart, return_date=None, fare_type="USD"):
    """Navigate to SW results and extract flight data."""
    url = build_url(origin, dest, depart, return_date, fare_type)
    page.goto(url, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(WAIT_FOR_RESULTS * 1000)

    # Dismiss cookie banner
    try:
        page.locator("button:has-text('Dismiss')").click(timeout=3000)
        page.wait_for_timeout(1000)
    except:
        pass

    # Verify we're on the results page
    if "select-depart" not in page.url and "select.html" not in page.url:
        return []

    # Extract from [role='main'] (NOT <main> which is the booking form)
    text = page.frames[0].evaluate(
        """() => { var el = document.querySelector("[role='main']"); return el ? el.innerText : ''; }"""
    )

    blocks = re.findall(r"(# [\d/ ]+.*?View seats)", text, re.DOTALL)
    flights = []
    for block in blocks:
        flight = parse_flight_block(block)
        if flight.get("fares"):
            flights.append(flight)

    return flights


def search(origin, dest, depart, return_date=None, show_points=False, as_json=False):
    """Run the full SW search with Patchright."""
    tmpdir = tempfile.mkdtemp(prefix="sw_")

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

            # Visit homepage first to establish a normal browsing session
            page.goto(HOMEPAGE, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)

            # Fetch cash fares
            cash_flights = fetch_flights(page, origin, dest, depart, return_date, "USD")

            # Fetch points fares (separate URL, not a toggle)
            points_flights = []
            if show_points:
                points_flights = fetch_flights(
                    page, origin, dest, depart, return_date, "POINTS"
                )

            browser.close()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    result = {
        "origin": origin,
        "destination": dest,
        "departure_date": depart,
        "return_date": return_date,
        "cash_flights": cash_flights,
        "points_flights": points_flights,
    }

    if as_json:
        print(json.dumps(result, indent=2))
    else:
        print_tables(origin, dest, depart, cash_flights, points_flights)

    return result


def fmt_stops(f):
    s = f.get("stops", "?")
    conn = f.get("connection", "")
    return f"{s} via {conn}" if conn else s


def print_flights(flights, label):
    print(f"\n{label}")
    is_points = flights[0].get("fare_type") == "points" if flights else False
    w = 14 if is_points else 9

    header = (
        f"{'Flight':<12} {'Depart':<8} {'Arrive':<10} {'Stops':<16} {'Dur':<8} "
        f"{'Basic':<{w}} {'Choice':<{w}} {'Ch Pref':<{w}} {'Ch Extra':<{w}}"
    )
    print(header)
    print("-" * len(header))

    for f in flights:
        num = f"#{f.get('flight_number', '?')}"
        dep = f.get("depart_time", "?")
        arr = f.get("arrive_time", "?")
        stops = fmt_stops(f)
        dur = f.get("duration", "?")
        fares = f.get("fares", {})
        basic = fares.get("Basic", "")
        choice = fares.get("Choice", "")
        ch_pref = fares.get("Choice Preferred", "")
        ch_extra = fares.get("Choice Extra", "")
        print(
            f"{num:<12} {dep:<8} {arr:<10} {stops:<16} {dur:<8} "
            f"{basic:<{w}} {choice:<{w}} {ch_pref:<{w}} {ch_extra:<{w}}"
        )


def print_tables(origin, dest, depart, cash_flights, points_flights):
    print(f"\nSouthwest {origin} -> {dest} on {depart}")
    print(f"{'=' * 95}")

    if cash_flights:
        print_flights(cash_flights, f"CASH FARES ({len(cash_flights)} flights):")
    else:
        print("No cash flights found.")

    if points_flights:
        print_flights(
            points_flights, f"\nPOINTS FARES ({len(points_flights)} flights):"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search Southwest fares")
    parser.add_argument("--origin", required=True, help="Origin airport code")
    parser.add_argument("--dest", required=True, help="Destination airport code")
    parser.add_argument("--depart", required=True, help="Departure date YYYY-MM-DD")
    parser.add_argument("--return", dest="return_date", help="Return date YYYY-MM-DD")
    parser.add_argument(
        "--points", action="store_true", help="Also show points pricing"
    )
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    search(
        args.origin, args.dest, args.depart, args.return_date, args.points, args.json
    )
