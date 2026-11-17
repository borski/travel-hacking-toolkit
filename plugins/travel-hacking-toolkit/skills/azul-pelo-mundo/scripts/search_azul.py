#!/usr/bin/env python3
"""
Azul Pelo Mundo (Azul Fidelidade) points search via Patchright.

azulpelomundo.voeazul.com.br prices Azul and partner flights (TAP, United,
Emirates, ...) in Azul Fidelidade points, plus points + cash ("Pontos +
dinheiro") combos. No login is needed to search.

The site sits behind Akamai Bot Manager and its JSON endpoint
(/api/availability) requires a reCAPTCHA token minted by the page itself, so a
plain HTTP call gets 403 / "reCAPTCHA token is required". We therefore load the
public results URL in a real, headed browser (same approach as the vrbo skill)
and capture the /api/availability response the page fetches for itself. We
never mint tokens or call the endpoint directly.

Usage:
    # One-way, 1 adult
    python3 search_azul.py --origin GRU --dest LIS --depart 2027-03-10 --json

    # Round trip, 2 adults + 1 lap infant
    python3 search_azul.py --origin GRU --dest LIS --depart 2027-03-10 \
        --return 2027-03-24 --adults 2 --infants 1 --json

Environment:
    AZUL_PROFILE   Profile directory (default: ~/.azul-profiles/default).
                   In Docker, a tmp profile is used automatically.

Exit codes:
    0  results found (or empty result set with no error)
    1  blocked / no availability response captured
    2  bad arguments
"""

import argparse
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path


BASE_URL = "https://azulpelomundo.voeazul.com.br"
API_PATH = "/api/availability"

BLOCK_MARKERS = (
    "Access Denied",
    "Too Many Requests",
    "verify you are human",
    "Pardon Our Interruption",
    "reCAPTCHA token is required",
)


def in_docker():
    return Path("/.dockerenv").exists() or os.environ.get("AZUL_IN_DOCKER") == "1"


def get_profile_dir():
    if in_docker():
        return tempfile.mkdtemp(prefix="azul-")
    env_dir = os.environ.get("AZUL_PROFILE")
    if env_dir:
        return env_dir
    return str(Path.home() / ".azul-profiles" / "default")


def validate_iata(code):
    code = (code or "").strip().upper()
    if not re.fullmatch(r"[A-Z]{3}", code):
        raise ValueError(f"invalid IATA code: {code!r}")
    return code


def validate_date(value):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value or ""):
        raise ValueError(f"invalid date (expected YYYY-MM-DD): {value!r}")
    return value


def build_results_url(origin, dest, depart, ret=None, adults=1, children=0,
                      infants=0, cabin="ECONOMY"):
    """Build the public results URL the site's own search form navigates to.

    Path layout (captured from the live site):
      /flights/{OW|RT}/{ORIG}/{DEST}/-/-/{DEPART}/{RETURN|-}/{ADT}/{CHD}/{INF}/0/0/ALL/F/{CABIN}/-/-/-/-/A/-
    """
    trip = "RT" if ret else "OW"
    parts = [
        "flights", trip, origin, dest, "-", "-", depart, ret or "-",
        str(adults), str(children), str(infants), "0", "0",
        "ALL", "F", cabin, "-", "-", "-", "-", "A", "-",
    ]
    return f"{BASE_URL}/" + "/".join(parts)


def text_has_block_marker(text):
    if not text:
        return False
    low = text.lower()
    return any(marker.lower() in low for marker in BLOCK_MARKERS)


def _segments(flight):
    return [
        {
            "flight": f"{g.get('marketingCarrier', '')}{g.get('flightNumber', '')}",
            "operatingCarrier": g.get("operatingCarrier"),
            "from": g.get("origin"),
            "to": g.get("destination"),
            "departure": f"{g.get('departureDate')} {g.get('departureTime')}",
            "arrival": f"{g.get('arrivalDate')} {g.get('arrivalTime')}",
        }
        for g in flight.get("flightGroup") or []
    ]


def _cash_prices(prices):
    """Map passenger type -> cash fare (BRL) from a `prices` list."""
    out = {}
    for p in prices or []:
        if p.get("passenger") and p.get("value") is not None:
            out[p["passenger"]] = p["value"]
    return out


def _ranges(ranges):
    return [
        {"points": r.get("points"), "cashBRL": r.get("amount")}
        for r in ranges or []
        if r.get("points") is not None
    ]


def parse_availability(payload):
    """Flatten an /api/availability response into one row per itinerary.

    Pure (no browser). For round trips each outbound option lists its return
    pairings in recommendations[].returnFlights[].categories[]. The category
    carries the RETURN leg's points and cash fare only (verified on the live
    site: the outbound shows 88,500 and the return list shows 84,000 for the
    same pairing), so the round-trip price is outbound + return.
    """
    data = (payload or {}).get("data") or {}
    dep_block = data.get("departureFlights") or {}
    ret_block = data.get("returnFlights") or {}
    ret_by_id = {f.get("id"): f for f in ret_block.get("flights") or []}

    rows = []
    for flight in dep_block.get("flights") or []:
        base = {
            "fareType": flight.get("fareOriginType"),
            "marketingCarrier": flight.get("marketingCarrier"),
            "operatingCarriers": flight.get("operatingCarriers") or [],
            "stops": flight.get("connection"),
            "durationHHMM": flight.get("elapsedFlightTime"),
            "checkedBags": ((flight.get("baggage") or [{}])[0]).get("quantity"),
            "lowAvailability": flight.get("hasLowAvailability"),
            "outbound": {
                "departure": f"{flight.get('departureDate')} {flight.get('departureTime')}",
                "arrival": f"{flight.get('finalArrivalDate')} {flight.get('finalArrivalTime')}",
                "segments": _segments(flight),
            },
        }

        recs = flight.get("recommendations") or []
        combos = []
        for rec in recs:
            for rf in rec.get("returnFlights") or []:
                for cat in rf.get("categories") or []:
                    combos.append((rf.get("id"), cat))

        if not combos:
            fee = ((recs[0].get("fee") or {}).get("total") or {}) if recs else {}
            rows.append({
                **base,
                "tripType": "ONE_WAY",
                "points": (flight.get("points") or {}).get("value"),
                "pointsPlusCash": _ranges(flight.get("ranges")),
                "feesBRL": fee.get("value"),
                "cashFareBRL": _cash_prices(flight.get("prices")),
            })
            continue

        out_points = (flight.get("points") or {}).get("value")
        out_cash = _cash_prices(flight.get("prices"))
        for ret_id, cat in combos:
            ret_flight = ret_by_id.get(ret_id) or {}
            fee = (cat.get("fee") or {}).get("total") or {}
            ret_points = (cat.get("points") or {}).get("value")
            ret_cash = _cash_prices(cat.get("prices"))
            rows.append({
                **base,
                "tripType": "ROUND_TRIP",
                "points": (out_points or 0) + (ret_points or 0) if out_points and ret_points else None,
                "outboundPoints": out_points,
                "returnPoints": ret_points,
                "pointsPlusCash": {
                    "outbound": _ranges(flight.get("ranges")),
                    "return": _ranges(cat.get("ranges")),
                },
                "feesBRL": fee.get("value"),
                "cashFareBRL": {k: round(out_cash.get(k, 0) + ret_cash.get(k, 0), 2)
                                for k in set(out_cash) | set(ret_cash)},
                "checkedBags": ((cat.get("baggageRule") or {}).get("quantity", base["checkedBags"])),
                "inbound": {
                    "departure": f"{ret_flight.get('departureDate')} {ret_flight.get('departureTime')}",
                    "arrival": f"{ret_flight.get('finalArrivalDate')} {ret_flight.get('finalArrivalTime')}",
                    "segments": _segments(ret_flight),
                } if ret_flight else None,
            })

    rows = [r for r in rows if r.get("points")]
    rows.sort(key=lambda r: r["points"])
    return rows


def cents_per_point(row):
    """BRL centavos per point when paying the adult cash fare instead.

    `points` is per adult (verified: the same itinerary shows the same points
    for 1 adult and for 2 adults + 1 infant), so compare it to the adult fare.
    Returns None when the cash fare is not public (AWARD inventory shows 0).
    """
    adult = (row.get("cashFareBRL") or {}).get("ADULT") or 0
    if not adult or not row.get("points"):
        return None
    return round(adult / row["points"] * 100, 2)


def search(args):
    profile_dir = get_profile_dir()
    os.makedirs(profile_dir, exist_ok=True)

    from patchright.sync_api import sync_playwright

    url = build_results_url(
        args.origin, args.dest, args.depart, args.ret,
        args.adults, args.children, args.infants, args.cabin,
    )
    payloads = []
    blocked_statuses = []

    def on_response(resp):
        if API_PATH not in resp.url:
            return
        if resp.status >= 400:
            blocked_statuses.append(resp.status)
            return
        try:
            payloads.append(resp.json())
        except Exception:
            pass

    with sync_playwright() as p:
        launch = dict(
            user_data_dir=profile_dir,
            headless=False,  # Akamai flags headless — run headed (Xvfb in Docker)
            viewport={"width": 1400, "height": 900},
            locale="pt-BR",
        )
        try:
            ctx = p.chromium.launch_persistent_context(
                channel="chrome" if not in_docker() else None, **launch
            )
        except Exception:
            ctx = p.chromium.launch_persistent_context(**launch)

        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.on("response", on_response)

        for attempt in range(1, args.retries + 1):
            try:
                page.goto(BASE_URL + "/", wait_until="domcontentloaded", timeout=45000)
                time.sleep(2.5)
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                deadline = time.time() + 30
                while not payloads and time.time() < deadline:
                    time.sleep(1)
                if payloads and (payloads[-1] or {}).get("data"):
                    break
                if blocked_statuses:
                    reason = f"availability API returned HTTP {blocked_statuses[-1]} (bot wall)"
                else:
                    try:
                        body = page.evaluate("() => document.body ? document.body.innerText.slice(0, 400) : ''")
                    except Exception:
                        body = ""
                    reason = "block/challenge page" if text_has_block_marker(body) else "no availability response"
                print(f"[attempt {attempt}] {reason}, retrying…", file=sys.stderr)
                payloads.clear()
                blocked_statuses.clear()
                time.sleep(4 * attempt)
            except Exception as e:
                print(f"[attempt {attempt}] navigation error: {e}", file=sys.stderr)
                time.sleep(3 * attempt)

        try:
            final_url = page.url
            ctx.close()
        except Exception:
            final_url = url

    good = [pl for pl in payloads if (pl or {}).get("data")]
    if not good:
        print(
            "ERROR: no availability captured from Azul Pelo Mundo (Akamai / "
            "reCAPTCHA wall or no flights). Space searches a few minutes apart "
            "and retry, or open this URL in a normal browser:\n"
            f"  {url}",
            file=sys.stderr,
        )
        sys.exit(1)

    rows = []
    for pl in good:
        rows.extend(parse_availability(pl))
    rows.sort(key=lambda r: r["points"])
    passengers = {"adults": args.adults, "children": args.children, "infants": args.infants}
    for r in rows:
        r["cashValueCentsPerPoint"] = cents_per_point(r)
    if args.limit:
        rows = rows[: args.limit]

    return {
        "source": "azul-pelo-mundo",
        "searchUrl": final_url,
        "query": {
            "origin": args.origin, "destination": args.dest,
            "depart": args.depart, "return": args.ret,
            **passengers, "cabin": args.cabin,
        },
        "pointsArePerAdult": True,
        "count": len(rows),
        "itineraries": rows,
    }


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="Azul Pelo Mundo points search via Patchright")
    ap.add_argument("--origin", required=True, help="Origin IATA, e.g. GRU")
    ap.add_argument("--dest", required=True, help="Destination IATA, e.g. LIS")
    ap.add_argument("--depart", required=True, help="Departure date YYYY-MM-DD")
    ap.add_argument("--return", dest="ret", help="Return date YYYY-MM-DD (omit for one-way)")
    ap.add_argument("--adults", type=int, default=1)
    ap.add_argument("--children", type=int, default=0, help="Children 2-11")
    ap.add_argument("--infants", type=int, default=0, help="Lap infants under 2")
    ap.add_argument("--cabin", default="ECONOMY", choices=["ECONOMY", "BUSINESS", "FIRST"])
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--json", action="store_true", help="Emit JSON to stdout")
    args = ap.parse_args(argv)
    try:
        args.origin = validate_iata(args.origin)
        args.dest = validate_iata(args.dest)
        args.depart = validate_date(args.depart)
        if args.ret:
            args.ret = validate_date(args.ret)
    except ValueError as e:
        ap.print_usage(sys.stderr)
        print(f"error: {e}", file=sys.stderr)
        sys.exit(2)
    return args


def main():
    args = parse_args()
    result = search(args)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    print(f"Azul Pelo Mundo — {result['count']} itineraries", file=sys.stderr)
    print(f"  {result['searchUrl']}\n", file=sys.stderr)
    for r in result["itineraries"]:
        carriers = "/".join(r["operatingCarriers"]) or r.get("marketingCarrier") or "?"
        stops = "direto" if r.get("stops") == 0 else f"{r.get('stops')} parada(s)"
        print(f"• {r['points']:,} pts + R$ {r.get('feesBRL') or 0:,.2f} taxas  [{carriers}, {stops}, {r.get('fareType')}]")
        print(f"    ida {r['outbound']['departure']} → {r['outbound']['arrival']}")
        if r.get("inbound"):
            print(f"    volta {r['inbound']['departure']} → {r['inbound']['arrival']}")
        if r.get("cashValueCentsPerPoint"):
            print(f"    valor: {r['cashValueCentsPerPoint']} centavos/ponto vs tarifa em dinheiro")


if __name__ == "__main__":
    main()
