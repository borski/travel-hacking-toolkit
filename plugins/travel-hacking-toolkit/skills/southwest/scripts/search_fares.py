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


FLIGHT_HEADER_RE = re.compile(r"^# ((?:WN)?\d+(?:\s*/\s*(?:WN)?\d+)*)\s*$", re.M)
FARE_LABEL_RE = re.compile(
    r"^Departs [^\n]*?\.\s*(Basic|Choice Preferred|Choice Extra|Choice)\s*$", re.M
)


def split_flight_blocks(text):
    """Split [role='main'] text into one chunk per flight card.

    SW renders each card as a "# WN1234" (or "# WN1 / WN2") header line,
    followed by times, stops, duration, then one accessibility label per
    fare ("Departs 7:00 AM, arrives 8:25 AM, nonstop, ... Basic") with the
    price lines beneath it. The last card runs into the footer, so each
    block is trimmed at the first blank line after its final fare.
    """
    heads = list(FLIGHT_HEADER_RE.finditer(text))
    blocks = []
    for i, h in enumerate(heads):
        stop = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        chunk = text[h.start():stop]
        labels = list(FARE_LABEL_RE.finditer(chunk))
        if labels:
            tail = chunk[labels[-1].end():]
            cut = re.search(r"\n\s*\n", tail)
            if cut:
                chunk = chunk[: labels[-1].end() + cut.start()]
        blocks.append(chunk)
    return blocks


def parse_fare_cell(cell, fare_type):
    """Parse the lines under one fare label. Returns (price_str, seats_left)."""
    cell = cell.strip()
    left = re.search(r"^(\d+) left$", cell, re.M)
    seats_left = int(left.group(1)) if left else None
    if not cell or cell.startswith("Unavailable") or cell.startswith("Sold out"):
        return "Unavail", None
    if fare_type == "points":
        pts = re.search(r"^([\d,]+) Points$", cell, re.M)
        if not pts:
            return "Unavail", None
        tax = re.search(r"^([\d,]+(?:\.\d{2})?) Dollars$", cell, re.M)
        tax_str = f" +${tax.group(1)}" if tax else ""
        return f"{pts.group(1)} pts{tax_str}", seats_left
    # Cash: the first "N Dollars" line is the fare. "earn N Points" lines are
    # Rapid Rewards earnings, not a price, so ignore them.
    usd = re.search(r"^([\d,]+) Dollars$", cell, re.M)
    if not usd:
        return "Unavail", None
    return f"${usd.group(1)}", seats_left


def parse_flight_block(text, fare_type="cash"):
    """Parse a single flight card into structured data."""
    flight = {}

    m = FLIGHT_HEADER_RE.search(text)
    if m:
        # SW now prints "WN2335" / "WN2427 / WN955". Strip the carrier
        # prefix so numbers stay "2335" / "2427 / 955", matching the
        # flight_number format monitor.py configs already use.
        num = re.sub(r"WN", "", m.group(1))
        flight["flight_number"] = re.sub(r"\s*/\s*", " / ", num).strip()

    header = FARE_LABEL_RE.split(text, maxsplit=1)[0]

    times = re.findall(r"(\d{1,2}:\d{2}\s?(?:AM|PM))", header)
    if len(times) >= 2:
        flight["depart_time"] = times[0].replace(" ", "")
        flight["arrive_time"] = times[1].replace(" ", "")

    if re.search(r"^Nonstop$", header, re.M | re.I):
        flight["stops"] = "Nonstop"
    else:
        sm = re.search(r"(\d+)\s*stops?", header, re.I)
        flight["stops"] = f"{sm.group(1)} stop" if sm else "?"
        conn = re.search(r"(?:plane change|Change planes)\s+([A-Z]{3})", header, re.I)
        if conn:
            flight["connection"] = conn.group(1).upper()

    m = re.search(r"(\d+h\s*\d+m)", header)
    if m:
        flight["duration"] = m.group(1)

    labels = list(FARE_LABEL_RE.finditer(text))
    if labels:
        flight["fares"] = {}
        flight["fare_type"] = fare_type
        low = False
        for i, lab in enumerate(labels):
            end = labels[i + 1].start() if i + 1 < len(labels) else len(text)
            price, left = parse_fare_cell(text[lab.end():end], fare_type)
            flight["fares"][lab.group(1)] = price
            if left is not None:
                low = True
        if low:
            flight["low_inventory"] = True

    return flight


def _legacy_parse_flight_block(text):
    """Pre-Nov-2026 SW layout parser, kept as a fallback."""
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


def _load_results_text(page, url):
    """Load a results URL and return the [role='main'] text ('' on failure)."""
    page.goto(url, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(WAIT_FOR_RESULTS * 1000)

    # Dismiss cookie banner
    try:
        page.locator("button:has-text('Dismiss')").click(timeout=3000)
        page.wait_for_timeout(1000)
    except Exception:
        pass

    # Verify we're on the results page
    if "select-depart" not in page.url and "select.html" not in page.url:
        print(f"[sw] not a results page: {page.url}", file=sys.stderr)
        return ""

    # Extract from [role='main'] (NOT <main> which is the booking form)
    return page.frames[0].evaluate(
        """() => { var el = document.querySelector("[role='main']"); return el ? el.innerText : ''; }"""
    )


def _parse_results_text(text, fare_type):
    kind = "points" if fare_type == "POINTS" else "cash"
    flights = []
    for block in split_flight_blocks(text):
        flight = parse_flight_block(block, kind)
        if flight.get("fares"):
            flights.append(flight)

    if not flights:
        # Older layout: "# 1234 ... View seats"
        for block in re.findall(r"(# [\d/ ]+.*?View seats)", text, re.DOTALL):
            flight = _legacy_parse_flight_block(block)
            if flight.get("fares"):
                flights.append(flight)
    return flights


def fetch_flights(page, origin, dest, depart, return_date=None, fare_type="USD", attempts=2):
    """Navigate to SW results and extract flight data.

    The first results load after the homepage warmup sometimes renders an
    empty shell, so retry once before giving up.
    """
    url = build_url(origin, dest, depart, return_date, fare_type)
    for attempt in range(1, attempts + 1):
        text = _load_results_text(page, url)
        flights = _parse_results_text(text, fare_type)
        if flights:
            return flights
        print(
            f"[sw] {fare_type} attempt {attempt}: 0 flights "
            f"(text {len(text)} chars, url {page.url})",
            file=sys.stderr,
        )
    return []


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
    w = 18 if is_points else 9

    header = (
        f"{'Flight':<18} {'Depart':<8} {'Arrive':<10} {'Stops':<16} {'Dur':<8} "
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
            f"{num:<18} {dep:<8} {arr:<10} {stops:<16} {dur:<8} "
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
