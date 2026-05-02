#!/usr/bin/env python3
"""TicketsAtWork hotel search via Patchright.

Logs into ticketsatwork.com, runs a hotel search, and returns parsed
listings as JSON. No public API exists; this is the cleanest scrape path.

Usage:
    TAW_USER=... TAW_PASS=... python3 search_hotels.py \
        --city "Carlsbad, CA" --checkin 2027-03-04 --checkout 2027-03-07 \
        [--rooms 1] [--adults 2] [--children 0] [--json] [--debug]

See SKILL.md for the parsed output schema and gotchas.
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


def search_hotels(page, city, checkin, checkout, rooms, adults, children, debug=False):
    """Run the hotel search and return raw HTML of the results page."""
    if "/tickets" not in page.url:
        page.goto(f"{HOMEPAGE}/tickets/", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)

    # Click the Hotel tab to make the search form active
    try:
        tab = page.locator("[data-tab-id='#hotel_search']").first
        if tab.is_visible(timeout=2000):
            tab.click(timeout=3000)
            page.wait_for_timeout(1500)
            log("clicked hotel tab")
    except Exception as e:
        log(f"hotel tab click failed (may already be active): {e}")

    shot(page, "hotels_03_tab", debug)

    # Fill destination via autocomplete (populates lat/lng hidden fields)
    if not fill_autocomplete(
        page, "#place_name", "#place_lat", "#place_lng", city,
        debug=debug, label="hotel destination",
    ):
        log("ERROR: could not select destination after retries")
        dump_html(page, "hotels_05_no_destination", debug)
        return None

    shot(page, "hotels_05_destination_selected", debug)

    # Set dates via JS (inputs are readonly + jQuery datepicker driven)
    checkin_str = fmt_date_taw(checkin)
    checkout_str = fmt_date_taw(checkout)
    log(f"setting check_in={checkin_str} check_out={checkout_str}")
    page.evaluate(
        """([ci, co]) => {
            const setVal = (sel, v) => {
                const el = document.querySelector(sel);
                if (!el) return false;
                const proto = Object.getPrototypeOf(el);
                Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, v);
                el.dispatchEvent(new Event('input', {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
            };
            setVal('#check_in', ci);
            setVal('#check_out', co);
        }""",
        [checkin_str, checkout_str],
    )

    # Set rooms and occupants via JS
    page.evaluate(
        """([rooms, adults, children]) => {
            const set = (sel, v) => {
                const el = document.querySelector(sel);
                if (el) el.value = String(v);
            };
            set('input[name="rooms"]', rooms);
            set('input[name="room_occupants[0][adults]"]', adults);
            set('input[name="room_occupants[0][children]"]', children);
        }""",
        [rooms, adults, children],
    )

    shot(page, "hotels_06_form_filled", debug)

    log("submitting search...")
    submitted = page.evaluate(
        """() => {
            const form = document.querySelector('#hotel_search');
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
        page.wait_for_url(re.compile(r"hotels\.php"), timeout=30000)
    except PwTimeout:
        log(f"WARNING: didn't reach hotels.php (URL: {page.url})")

    log("waiting for hotel cards to render...")
    try:
        page.wait_for_selector(
            'li[id^="hotel_"][data-name]',
            timeout=30000,
            state="attached",
        )
        log("first hotel card detected")
    except PwTimeout:
        log("WARNING: no hotel cards rendered within 30s")

    page.wait_for_timeout(3000)
    shot(page, "hotels_07_results", debug)
    dump_html(page, "hotels_07_results", debug)

    return page.content()


def parse_results(html):
    """Extract hotel listings from search results HTML.

    See SKILL.md for the output schema. TaW renders cards as:
        <li id="hotel_NNN_x" data-name=... data-price=... ...>...</li>
    """
    listings = []

    card_pattern = re.compile(
        r'<li[^>]*\bid="(hotel_[^"]+)"[^>]*?(\s+data-[^>]+)>(.*?)</li>',
        re.DOTALL,
    )

    def attr(blob, name):
        m = re.search(rf'\bdata-{name}="([^"]*)"', blob)
        return m.group(1) if m else None

    def inner(chunk, pattern):
        m = re.search(pattern, chunk, re.DOTALL)
        return m.group(1).strip() if m else None

    for m in card_pattern.finditer(html):
        card_id, attrs_blob, body = m.group(1), m.group(2), m.group(3)
        name = attr(attrs_blob, "name")
        if not name:
            continue

        listing = {
            "id": card_id,
            "name": (
                unescape(inner(body, r"<h2[^>]*>([^<]+)</h2>")) or name.title()
            ),
            "name_normalized": name,
            "rating": to_float(attr(attrs_blob, "rating")),
            "guest_rating": to_float(attr(attrs_blob, "guest-rating")),
            "price_per_night_usd": to_int(attr(attrs_blob, "price")),
            "distance_miles": to_float(attr(attrs_blob, "distance")),
            "property_type": attr(attrs_blob, "property-type"),
            "lat": to_float(attr(attrs_blob, "lat")),
            "lng": to_float(attr(attrs_blob, "lng")),
            "tripadvisor": to_float(attr(attrs_blob, "tripadvisor")),
            "room_id": attr(attrs_blob, "room-id"),
            "rate_code": attr(attrs_blob, "rate-code"),
            "featured": attr(attrs_blob, "featured") == "1",
            "discount_ranking": to_float(attr(attrs_blob, "discount_ranking")),
        }

        total = inner(
            body,
            r'<div class="fw-bold">\s*<span>\$([\d,]+)</span>\s*<span class="total-label',
        )
        if total:
            listing["total_price_usd"] = to_int(total)

        strike = inner(body, r'<s class="st-price[^>]*">\$([\d,]+)</s>')
        if strike:
            listing["strike_price_usd"] = to_int(strike)

        save = inner(
            body, r'class="hotel-save-label[^>]*">Save \$([\d,.]+)</span>'
        )
        if save:
            listing["savings_usd"] = to_float(save)

        pts = inner(
            body,
            r'class="text-uppercase fw-bold">Earn ([\d,]+) Points</span>',
        )
        if pts:
            listing["loyalty_points"] = to_int(pts)

        url = inner(body, r'href="(/tickets/hotels\.php\?sub=details[^"]+)"')
        if url:
            listing["detail_url"] = HOMEPAGE + url.replace("&amp;", "&")

        dist_label = unescape(
            inner(body, r'<span class="hotel-distance">([^<]+)</span>')
        )
        if dist_label:
            listing["distance_label"] = dist_label

        listings.append(listing)

    return listings


def get_pagination_info(page):
    """Read the pagination state for display purposes only.

    TaW renders ALL listings in the initial DOM and uses simple-pagination
    to chunk them visually. There are no additional results beyond what's
    already parseable from page 1.
    """
    return page.evaluate(
        """() => {
            const pager = document.querySelector('#pager');
            if (!pager) return {current_page: 1, total_pages: 1};
            const links = Array.from(pager.querySelectorAll('a.page-link'));
            const nums = links
                .map(a => parseInt((a.getAttribute('href') || '').replace('#page-', ''), 10))
                .filter(n => !isNaN(n));
            const cur = parseInt(
                (pager.querySelector('.current')?.innerText || '1').trim(), 10
            ) || 1;
            const max = nums.length ? Math.max(...nums, cur) : cur;
            return {current_page: cur, total_pages: max};
        }"""
    )


def main():
    parser = argparse.ArgumentParser(description="Search TicketsAtWork hotels")
    parser.add_argument("--city", required=True, help="Destination city or address")
    parser.add_argument("--checkin", required=True, help="Check-in date (YYYY-MM-DD)")
    parser.add_argument(
        "--checkout", required=True, help="Check-out date (YYYY-MM-DD)"
    )
    parser.add_argument("--rooms", type=int, default=1)
    parser.add_argument("--adults", type=int, default=2)
    parser.add_argument("--children", type=int, default=0)
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument(
        "--raw-html-out",
        help="Write the raw results HTML to a file for analysis",
    )
    args = parser.parse_args()

    user = os.environ.get("TAW_USER")
    pw = os.environ.get("TAW_PASS")
    if not user or not pw:
        log("ERROR: TAW_USER and TAW_PASS environment variables required")
        sys.exit(1)

    log(f"creds loaded (user len={len(user)}, pass len={len(pw)})")

    listings = []
    pagination = {"current_page": 1, "total_pages": 1}
    raw_html = None

    tmpdir = tempfile.mkdtemp(prefix="taw_")
    try:
        with sync_playwright() as p:
            ctx = make_browser_context(p, tmpdir)
            page = ctx.pages[0] if ctx.pages else ctx.new_page()

            if not login(page, user, pw, args.debug):
                log("login failed")
                ctx.close()
                sys.exit(2)

            html = search_hotels(
                page, args.city, args.checkin, args.checkout,
                args.rooms, args.adults, args.children, args.debug,
            )

            if html is None:
                log("search failed; no results HTML")
                ctx.close()
                sys.exit(3)

            raw_html = html
            listings = parse_results(html)
            pagination = get_pagination_info(page)
            log(
                f"parsed {len(listings)} listings "
                f"(spread across {pagination['total_pages']} display pages)"
            )

            ctx.close()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    if args.raw_html_out and raw_html:
        Path(args.raw_html_out).write_text(raw_html)
        log(f"raw HTML saved: {args.raw_html_out}")

    seen = set()
    deduped = []
    for l in listings:
        if l.get("id") in seen:
            continue
        seen.add(l.get("id"))
        deduped.append(l)

    output = {
        "city": args.city,
        "checkin": args.checkin,
        "checkout": args.checkout,
        "rooms": args.rooms,
        "adults": args.adults,
        "children": args.children,
        "display_pages": pagination["total_pages"],
        "listing_count": len(deduped),
        "listings": deduped,
    }

    if args.json:
        print(json.dumps(output, indent=2))
    else:
        print(f"\nTicketsAtWork: {args.city}, {args.checkin} → {args.checkout}")
        print(f"  {args.rooms} room, {args.adults} adults, {args.children} children")
        print(
            f"  {len(deduped)} listings "
            f"(TaW splits into {output['display_pages']} display pages)"
        )
        priced = sorted(
            [l for l in deduped if l.get("total_price_usd")],
            key=lambda x: x["total_price_usd"],
        )
        for l in priced[:10]:
            stars = l.get("rating") or 0
            total = l.get("total_price_usd")
            per_night = l.get("price_per_night_usd")
            save = l.get("savings_usd")
            dist = l.get("distance_label") or ""
            save_str = f" (save ${save:.0f})" if save else ""
            print(
                f"    {stars:.1f}* | ${total} total | ${per_night}/night{save_str} | "
                f"{l.get('name', '?')} | {dist}"
            )


if __name__ == "__main__":
    main()
