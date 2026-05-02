#!/usr/bin/env python3
"""TicketsAtWork rental car search via Patchright.

Logs into ticketsatwork.com, runs a rental car search at a given pickup
location and date/time range, and dumps the parsed offer list as JSON.

Usage:
    TAW_USER=... TAW_PASS=... python3 search_cars.py \
        --pickup "San Diego Airport, CA" \
        --pickup-date 2027-03-04 --pickup-time 12:00 \
        --dropoff-date 2027-03-07 --dropoff-time 12:00 \
        [--dropoff "Los Angeles Airport, CA"] \
        [--age 30] [--json] [--debug]

If --dropoff is omitted, drops off at the same place as pickup.
Time format: 24-hour HH:MM, must be on a :00 or :30 boundary.
"""

import argparse
import json
import os
import re
import sys
import tempfile
import shutil
from pathlib import Path
from patchright.sync_api import sync_playwright, TimeoutError as PwTimeout

from taw_common import (
    HOMEPAGE,
    log,
    shot,
    dump_html,
    login,
    unescape,
    fill_autocomplete,
    fmt_date_taw,
    to_int,
    to_float,
    make_browser_context,
)


def search_cars(page, pickup, dropoff, pickup_date, pickup_time,
                dropoff_date, dropoff_time, age, debug=False):
    """Run the rental car search. Returns raw HTML of the results page."""
    if "/tickets" not in page.url:
        page.goto(f"{HOMEPAGE}/tickets/", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)

    # Click the Rental Car tab
    try:
        tab = page.locator("[data-tab-id='#rental_car_search']").first
        if tab.is_visible(timeout=2000):
            tab.click(timeout=3000)
            page.wait_for_timeout(1500)
            log("clicked rental car tab")
    except Exception as e:
        log(f"car tab click failed (may already be active): {e}")

    shot(page, "cars_03_tab", debug)

    # Pickup location autocomplete. The widget writes the resolved place
    # info into hidden fields with `data-value-goes-to` / `data-lat-lng-goes-to`
    # attributes. For the pickup input, those map to:
    #   #origin_search_value (the canonical place string)
    #   #origin_lat_lng (lat,lng pair)
    if not _fill_car_autocomplete(
        page, "#pickup_location", "#origin_search_value", "#origin_lat_lng",
        pickup, debug=debug, label="car pickup",
    ):
        log("ERROR: could not select pickup location after retries")
        dump_html(page, "cars_05_no_pickup", debug)
        return None

    # Dropoff (optional, defaults to pickup)
    if dropoff:
        log(f"setting dropoff: {dropoff}")
        if not _fill_car_autocomplete(
            page, "#dropoff_location", "#destination_search_value",
            "#destination_lat_lng", dropoff, debug=debug, label="car dropoff",
        ):
            log("WARNING: dropoff selection failed; falling back to same as pickup")
        else:
            page.evaluate(
                "() => { const el = document.querySelector('#destination_not_origin'); if (el) el.value = '1'; }"
            )

    # Dates and times via JS (inputs are readonly + datepicker driven)
    pu_date = fmt_date_taw(pickup_date)
    do_date = fmt_date_taw(dropoff_date)
    log(
        f"setting pick_up_date={pu_date} {pickup_time}, "
        f"drop_off_date={do_date} {dropoff_time}, age={age}"
    )
    page.evaluate(
        """([puDate, doDate, puTime, doTime, age]) => {
            const setVal = (sel, v) => {
                const el = document.querySelector(sel);
                if (!el) return;
                const proto = Object.getPrototypeOf(el);
                Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, v);
                el.dispatchEvent(new Event('input', {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
            };
            setVal('#pick_up_date', puDate);
            setVal('#drop_off_date', doDate);
            // Selects need a different approach to fire change
            const setSelect = (sel, v) => {
                const el = document.querySelector(sel);
                if (!el) return;
                el.value = v;
                el.dispatchEvent(new Event('change', {bubbles: true}));
            };
            setSelect('#pickup_time', puTime);
            setSelect('#dropoff_time', doTime);
            setSelect('#rc_age', String(age));
        }""",
        [pu_date, do_date, pickup_time, dropoff_time, age],
    )

    shot(page, "cars_06_form_filled", debug)

    log("submitting car search...")
    submitted = page.evaluate(
        """() => {
            const form = document.querySelector('#rental_car_search');
            if (!form) return false;
            const btn = form.querySelector('button[type="submit"]');
            if (btn) { btn.click(); return 'click'; }
            form.submit();
            return 'submit';
        }"""
    )
    if not submitted:
        return None
    log(f"submit method: {submitted}")

    log("waiting for results...")
    try:
        page.wait_for_url(re.compile(r"rentalcars"), timeout=30000)
    except PwTimeout:
        log(f"WARNING: didn't reach rentalcars URL (URL: {page.url})")

    # The car results page uses Handlebars templates that get filled via
    # XHR. The skeleton renders immediately with `{{var}}` placeholders;
    # actual offer data appears 5-30 seconds later. We wait for the
    # `{{total}}` placeholder in the rc-totals badge to be replaced with
    # a number, which signals that the API response landed and templates
    # rendered.
    log("waiting for car offer data to render (templates filling)...")
    try:
        page.wait_for_function(
            """() => {
                const el = document.querySelector('.rc-totals');
                if (!el) return false;
                const t = (el.innerText || '').trim();
                // After render: e.g. "32" or "0". Before: "{{total}}".
                return t !== '' && !t.includes('{{');
            }""",
            timeout=60000,
        )
        log("car results templates rendered")
    except PwTimeout:
        log("WARNING: car templates didn't fill within 60s")

    page.wait_for_timeout(4000)
    shot(page, "cars_07_results", debug)
    dump_html(page, "cars_07_results", debug)

    return page.content()


def _fill_car_autocomplete(page, input_sel, value_target_sel, latlng_target_sel,
                           query, debug=False, label="car_loc"):
    """Type into a rental-car location input and select a suggestion.

    The car autocomplete widget writes to two hidden targets:
    - `value_target_sel` (e.g. #origin_search_value): canonical place value
    - `latlng_target_sel` (e.g. #origin_lat_lng): "lat,lng" pair

    Empirically, lat/lng populates reliably but `value_target_sel` does NOT
    populate via the widget callback. The car backend needs a 3-letter
    airport code (IATA) for this field to resolve inventory.

    Strategy:
    1. Type query, wait for autocomplete dropdown
    2. Pick a suggestion, prefer one tagged as airport (fa-plane icon)
    3. Extract IATA code from suggestion text (e.g. "...(SAN)..." -> "SAN")
    4. Click the suggestion to populate latlng
    5. Manually set value_target to the IATA code (the form's missing piece)
    """
    iata_re = re.compile(r"\(([A-Z]{3})\)")

    for attempt in range(1, 4):
        log(f"{label} attempt {attempt}: typing '{query}' into {input_sel}")
        place = page.locator(input_sel)
        place.click(timeout=3000)

        page.evaluate(
            """([inSel, valSel, llSel]) => {
                const clear = (sel) => {
                    const el = document.querySelector(sel);
                    if (!el) return;
                    const proto = Object.getPrototypeOf(el);
                    Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, '');
                    el.dispatchEvent(new Event('input', {bubbles: true}));
                };
                clear(inSel);
                clear(valSel);
                clear(llSel);
            }""",
            [input_sel, value_target_sel, latlng_target_sel],
        )
        page.wait_for_timeout(500)

        place.type(query, delay=80, timeout=10000)
        page.wait_for_timeout(3500)
        shot(page, f"cars_autocomplete_{label}_a{attempt}", debug)

        # Get suggestion list. Prefer airport entries (fa-plane icon).
        suggestions = page.evaluate(
            """() => {
                const items = document.querySelectorAll(
                    '.ui-autocomplete.ebg-autocomplete .ui-menu-item:not(.ui-state-disabled)'
                );
                return Array.from(items).slice(0, 10).map((item, idx) => ({
                    idx: idx,
                    text: item.innerText || '',
                    is_airport: !!item.querySelector('.fa-plane'),
                }));
            }"""
        ) or []
        if not suggestions:
            log(f"{label}: no suggestions appeared")
            page.wait_for_timeout(2000)
            continue

        # Pick first airport suggestion if any, otherwise first suggestion
        pick_idx = None
        iata = None
        for s in suggestions:
            if s["is_airport"]:
                m = iata_re.search(s["text"])
                if m:
                    pick_idx = s["idx"]
                    iata = m.group(1)
                    break
        if pick_idx is None:
            # Try to extract IATA from any suggestion text
            for s in suggestions:
                m = iata_re.search(s["text"])
                if m:
                    pick_idx = s["idx"]
                    iata = m.group(1)
                    break
        if pick_idx is None:
            pick_idx = 0
            log(f"{label}: no airport suggestion; falling back to first ({suggestions[0]['text'][:60]})")

        log(f"{label}: picking suggestion {pick_idx} (iata={iata}): {suggestions[pick_idx]['text'][:80]}")

        # Click the chosen suggestion
        try:
            page.locator(
                ".ui-autocomplete.ebg-autocomplete .ui-menu-item:not(.ui-state-disabled)"
            ).nth(pick_idx).click(timeout=3000)
        except Exception as e:
            log(f"{label}: click failed: {e}")
            continue

        # Wait for latlng to populate
        try:
            page.wait_for_function(
                """([llSel]) => {
                    const ll = document.querySelector(llSel)?.value || '';
                    return ll !== '';
                }""",
                arg=[latlng_target_sel],
                timeout=8000,
            )
        except PwTimeout:
            log(f"{label}: latlng didn't populate within 8s")

        ll = page.evaluate(
            f"() => document.querySelector('{latlng_target_sel}')?.value || ''"
        )
        visible_text = page.evaluate(
            f"() => document.querySelector('{input_sel}')?.value || ''"
        )
        log(f"{label}: visible={visible_text!r} latlng={ll!r}")

        if ll:
            # Set value_target to the IATA code (the car backend wants this).
            # If we don't have an IATA from the suggestion, fall back to
            # extracting from the visible text.
            if not iata:
                m = iata_re.search(visible_text)
                if m:
                    iata = m.group(1)
            target_value = iata or visible_text
            page.evaluate(
                """([sel, val]) => {
                    const el = document.querySelector(sel);
                    if (el) {
                        el.value = val;
                        el.dispatchEvent(new Event('change', {bubbles: true}));
                    }
                }""",
                [value_target_sel, target_value],
            )
            log(f"{label}: set value_target={target_value!r}")
            return True

        log(f"{label} attempt {attempt} failed; retrying...")
        page.wait_for_timeout(2000)

    return False


def parse_results(html):
    """Extract rental car offers from the results page.

    The car results page structure is best-effort. We parse common patterns:
      - <li class="car-result-item" data-car-id=...>
      - <div class="rc-card" data-vendor=...>
    Schema is captured generically; specific class names may vary by deploy.
    Returns a list of offers with as much info as we can pull.
    """
    offers = []

    # Try multiple card patterns
    patterns = [
        # Generic: any <li> or <div> with id starting with car_ and data-* attrs
        re.compile(
            r'<(?:li|div)[^>]*\bid="(car_[^"]+)"[^>]*?(\s+data-[^>]+)>(.*?)</(?:li|div)>',
            re.DOTALL,
        ),
        # Pattern with class-based identification
        re.compile(
            r'<(?:li|div)[^>]*class="[^"]*(?:car-result|rc-result|rc-card)[^"]*"[^>]*?(\s+data-[^>]+)>(.*?)</(?:li|div)>',
            re.DOTALL,
        ),
    ]

    for pattern in patterns:
        for m in pattern.finditer(html):
            groups = m.groups()
            if len(groups) == 3:
                offer_id, attrs_blob, body = groups
            else:
                offer_id, attrs_blob, body = None, groups[0], groups[1]
            offer = _parse_car_card(offer_id, attrs_blob, body)
            if offer:
                offers.append(offer)
        if offers:
            break

    return offers


def _parse_car_card(card_id, attrs_blob, body):
    """Best-effort parse of one car card. Returns None if it doesn't look
    like a real offer (no name and no price)."""
    def attr(blob, name):
        m = re.search(rf'\bdata-{name}="([^"]*)"', blob)
        return m.group(1) if m else None

    def inner(chunk, pattern):
        m = re.search(pattern, chunk, re.DOTALL)
        return m.group(1).strip() if m else None

    offer = {
        "id": card_id,
        "vendor": attr(attrs_blob, "vendor") or attr(attrs_blob, "brand"),
        "car_class": attr(attrs_blob, "car-class") or attr(attrs_blob, "class"),
        "car_model": attr(attrs_blob, "car-model") or attr(attrs_blob, "model"),
        "transmission": attr(attrs_blob, "transmission"),
        "fuel": attr(attrs_blob, "fuel"),
        "passengers": to_int(attr(attrs_blob, "passengers")),
        "bags": to_int(attr(attrs_blob, "bags")),
        "doors": to_int(attr(attrs_blob, "doors")),
        "ac": attr(attrs_blob, "ac"),
        "price_per_day_usd": to_float(attr(attrs_blob, "price-per-day"))
            or to_float(attr(attrs_blob, "daily-rate")),
        "total_price_usd": to_float(attr(attrs_blob, "total-price"))
            or to_float(attr(attrs_blob, "price")),
    }

    # Look for prices in the inner body if data-attrs didn't have them
    if not offer.get("total_price_usd"):
        total = inner(body, r'\$([\d,.]+)\s*total') or inner(body, r'class="[^"]*total[^"]*"[^>]*>\$([\d,.]+)')
        if total:
            offer["total_price_usd"] = to_float(total)

    if not offer.get("price_per_day_usd"):
        per = inner(body, r'\$([\d,.]+)/day') or inner(body, r'\$([\d,.]+) per day')
        if per:
            offer["price_per_day_usd"] = to_float(per)

    name = unescape(inner(body, r'<h[1-4][^>]*>([^<]+)</h[1-4]>'))
    if name:
        offer["display_name"] = name

    # Detail / book URL
    url = inner(body, r'href="(/tickets/rentalcars[^"]+)"')
    if url:
        offer["detail_url"] = HOMEPAGE + url.replace("&amp;", "&")

    # Skip cards that don't look like real offers
    if not (offer.get("vendor") or offer.get("display_name") or offer.get("total_price_usd")):
        return None

    return {k: v for k, v in offer.items() if v is not None}


def main():
    parser = argparse.ArgumentParser(description="Search TicketsAtWork rental cars")
    parser.add_argument("--pickup", required=True, help="Pickup location")
    parser.add_argument("--dropoff", help="Dropoff location (default: same as pickup)")
    parser.add_argument(
        "--pickup-date", required=True, help="Pickup date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--pickup-time", default="12:00",
        help="Pickup time HH:MM (24h, :00 or :30 only). Default 12:00",
    )
    parser.add_argument(
        "--dropoff-date", required=True, help="Dropoff date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--dropoff-time", default="12:00",
        help="Dropoff time HH:MM. Default 12:00",
    )
    parser.add_argument(
        "--age", type=int, default=30,
        help="Driver age. TaW supports 20-25 with surcharge, 25+ standard. Default 30",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--raw-html-out")
    args = parser.parse_args()

    user = os.environ.get("TAW_USER")
    pw = os.environ.get("TAW_PASS")
    if not user or not pw:
        log("ERROR: TAW_USER and TAW_PASS environment variables required")
        sys.exit(1)

    log(f"creds loaded (user len={len(user)}, pass len={len(pw)})")

    raw_html = None
    offers = []

    tmpdir = tempfile.mkdtemp(prefix="taw_")
    try:
        with sync_playwright() as p:
            ctx = make_browser_context(p, tmpdir)
            page = ctx.pages[0] if ctx.pages else ctx.new_page()

            if not login(page, user, pw, args.debug):
                log("login failed")
                ctx.close()
                sys.exit(2)

            html = search_cars(
                page,
                pickup=args.pickup,
                dropoff=args.dropoff,
                pickup_date=args.pickup_date,
                pickup_time=args.pickup_time,
                dropoff_date=args.dropoff_date,
                dropoff_time=args.dropoff_time,
                age=args.age,
                debug=args.debug,
            )

            if html is None:
                log("car search failed; no results HTML")
                ctx.close()
                sys.exit(3)

            raw_html = html
            offers = parse_results(html)
            log(f"parsed {len(offers)} car offers")

            ctx.close()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    if args.raw_html_out and raw_html:
        Path(args.raw_html_out).write_text(raw_html)
        log(f"raw HTML saved: {args.raw_html_out}")

    output = {
        "pickup": args.pickup,
        "dropoff": args.dropoff or args.pickup,
        "pickup_at": f"{args.pickup_date} {args.pickup_time}",
        "dropoff_at": f"{args.dropoff_date} {args.dropoff_time}",
        "age": args.age,
        "offer_count": len(offers),
        "offers": offers,
    }

    if args.json:
        print(json.dumps(output, indent=2))
    else:
        print(
            f"\nTicketsAtWork rental cars: {args.pickup} → "
            f"{args.dropoff or args.pickup}"
        )
        print(f"  Pickup {args.pickup_date} {args.pickup_time}, "
              f"return {args.dropoff_date} {args.dropoff_time}, age {args.age}")
        print(f"  {len(offers)} offers")
        priced = sorted(
            [o for o in offers if o.get("total_price_usd")],
            key=lambda o: o["total_price_usd"],
        )
        for o in priced[:10]:
            vendor = o.get("vendor", "?")
            name = o.get("display_name", "?")
            total = o.get("total_price_usd")
            per_day = o.get("price_per_day_usd")
            per_day_str = f" (${per_day}/day)" if per_day else ""
            print(f"    ${total} total{per_day_str} | {vendor} | {name}")


if __name__ == "__main__":
    main()
