#!/usr/bin/env python3
"""TicketsAtWork ticket / attraction / Broadway / event browser.

TaW's travel-relevant ticket catalog is organized into curated landing
pages. This script handles:

  /tickets/pages.php?sub=<slug>                       theme parks, attractions
  /tickets/local_deals.php?sub=category&cat=events    live shows, concerts in
                                                      a destination

Each page renders a grid of "deals" with a title, subtitle (often a savings
claim), description, image, and a click-through URL. Most listings don't
show exact prices; pricing appears on the detail page. This script returns
the catalog; for exact prices, follow each deal's detail_url.

Usage:
    # Theme park / attraction category
    --category disneyland

    # Live events in your area (concerts, theater, sports)
    --section events

    # Free-text keyword (uses Reflektion search; lands on best-match page)
    --keyword "universal studios"

Common --category slugs (theme parks):
    wdw                 Walt Disney World
    disneyland          Disneyland Resort (California)
    disneyland-paris    Disneyland Paris
    usf                 Universal Orlando
    ush                 Universal Studios Hollywood
    seaworld            SeaWorld
    busch-gardens-parks Busch Gardens
    sesame-place        Sesame Place
    all-theme-parks-attractions

For an exhaustive list, see the SKILL.md documentation.
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
    make_browser_context,
)


def _wait_for_cards(page, debug=False):
    """Wait for any kind of TaW deal card to render.

    Different sections use different card classes:
      - pages.php (theme parks): li.grid-template-seen
      - local_deals.php: li.grid-template-seen on-hover
      - shopping.php: li[data-filter-key] inside ol.grid-list-product
    """
    log("waiting for deal cards...")
    try:
        page.wait_for_selector(
            "li.grid-template-seen, ol.grid-list-product li[data-filter-key]",
            timeout=20000,
            state="attached",
        )
        log("first deal card detected")
    except PwTimeout:
        log("WARNING: no deal cards rendered within 20s")
    page.wait_for_timeout(2000)


def browse_category(page, category, debug=False):
    """Load a theme-park / attraction category landing page.
    Path: /tickets/pages.php?sub=<slug>
    """
    url = f"{HOMEPAGE}/tickets/pages.php?sub={category}"
    log(f"loading category: {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(5000)

    # If TaW returns "Offer not available" (slug invalid), capture and bail
    title = page.evaluate("() => document.title || ''")
    if "Offer not available" in title:
        log(f"ERROR: slug '{category}' is not a valid TaW category page")
        return page.content()

    _wait_for_cards(page, debug)
    shot(page, f"tickets_category_{category}", debug)
    dump_html(page, f"tickets_category_{category}", debug)
    return page.content()


def browse_events(page, debug=False):
    """Load TaW's local events page (live shows, concerts, theater, sports
    by destination city). Travel-relevant subset of local_deals.

    Path: /tickets/local_deals.php?sub=category&cat=events
    """
    url = f"{HOMEPAGE}/tickets/local_deals.php?sub=category&cat=events"
    log(f"loading events: {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(5000)
    _wait_for_cards(page, debug)
    shot(page, "tickets_events", debug)
    dump_html(page, "tickets_events", debug)
    return page.content()


def search_keyword(page, keyword, debug=False):
    """Use the Reflektion site search via the top search bar.

    On Enter, TaW often redirects directly to the most relevant category
    landing page rather than showing a generic search results page. The
    landing page is parsed the same way as a categorical browse.
    """
    if "/tickets" not in page.url:
        page.goto(f"{HOMEPAGE}/tickets/", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)

    log(f"searching keyword: {keyword}")
    try:
        search_input = page.locator(".combined-search-control.rfk_sb").first
        search_input.click(timeout=3000)
        search_input.type(keyword, delay=80, timeout=10000)
        page.wait_for_timeout(2500)
        page.keyboard.press("Enter")
        page.wait_for_timeout(7000)
        log(f"after search: {page.url}")
    except Exception as e:
        log(f"keyword search failed: {e}")
        return None

    # Wait for whatever rendered to settle
    try:
        page.wait_for_selector(
            "li.grid-template-seen",
            timeout=15000,
            state="attached",
        )
    except PwTimeout:
        log("no deal cards on the search target page")

    page.wait_for_timeout(2000)
    shot(page, "tickets_keyword_results", debug)
    dump_html(page, "tickets_keyword_results", debug)

    return page.content()


def parse_deals(html):
    """Extract deal cards from a TaW catalog page.

    TaW renders deals in two related but distinct card formats:
    1. `<li class="grid-template-seen" data-type="..." data-unq="..." ...>`
       Used by: pages.php (theme parks), local_deals.php
       URL is in `data-unq` (or `data-link` on inner div)
       Type field tells you `ticket` vs `url`
    2. `<li data-filter-key="N" data-filter-id="N" data-filter-cat-id="...">`
       Used by: shopping.php
       URL is in `data-link` on a nested div, no data-type
       Cards lack the rich type/entity-id metadata of (1)

    Both have the same inner body fields:
      .grid-card-h1.list-title  or  .grid-card-h1     -> title
      .grid-card-h2                                   -> subtitle (savings claim)
      .grid-card-p                                    -> description (optional)
      style="--background-image-url: url('/...')"     -> image
    """
    deals = []

    # Two parallel patterns, both <li>-based
    patterns = [
        # Pattern 1: theme parks + local deals
        re.compile(
            r'<li[^>]*class="grid-template-seen[^"]*"[^>]*?(\s+data-[^>]+)>(.*?)</li>',
            re.DOTALL,
        ),
        # Pattern 2: shopping (data-filter-key but no grid-template-seen class)
        re.compile(
            r'<li\s+(data-filter-key="\d+"[^>]+)>(.*?)</li>',
            re.DOTALL,
        ),
    ]

    def attr(blob, name):
        m = re.search(rf'\bdata-{name}="([^"]*)"', blob)
        return m.group(1) if m else None

    def inner(chunk, pattern):
        m = re.search(pattern, chunk, re.DOTALL)
        return m.group(1).strip() if m else None

    for pattern in patterns:
        for m in pattern.finditer(html):
            attrs_blob, body = m.group(1), m.group(2)

            # Get the link. Try multiple attribute names + check for data-link
            # in the inner body (shopping uses inner data-link).
            link = (
                attr(attrs_blob, "unq")
                or attr(attrs_blob, "link")
                or inner(body, r'data-link="([^"]+)"')
            )
            if not link:
                continue

            title = inner(
                body,
                r'<div class="grid-card-h1 list-title[^"]*"[^>]*>([^<]+)</div>'
            ) or inner(
                body,
                r'<div class="grid-card-h1[^"]*"[^>]*>([^<]+)</div>'
            )
            subtitle = inner(
                body,
                r'<div class="grid-card-h2[^"]*"[^>]*>([^<]+)</div>'
            )
            desc_chunk = inner(
                body,
                r'<div class="grid-card-p"[^>]*>(.*?)</div>'
            )
            desc = None
            if desc_chunk:
                cleaned = re.sub(
                    r'<span id="ellipsis">.*', '', desc_chunk, flags=re.DOTALL
                )
                cleaned = re.sub(r'<a[^>]*>.*?</a>', '', cleaned, flags=re.DOTALL)
                cleaned = re.sub(r'<span[^>]*>.*?</span>', '', cleaned, flags=re.DOTALL)
                cleaned = re.sub(r'\s+', ' ', cleaned).strip()
                desc = cleaned or None

            img = inner(
                body,
                r"--background-image-url:\s*url\('([^']+)'\)"
            )

            if link.startswith("/"):
                absolute_url = HOMEPAGE + link
            elif link.startswith("http"):
                absolute_url = link
            else:
                absolute_url = HOMEPAGE + "/tickets/" + link
            absolute_url = absolute_url.replace("&amp;", "&")

            deal = {
                "type": attr(attrs_blob, "type"),
                "filter_entity_id": attr(attrs_blob, "filter-entity-id"),
                "filter_id": attr(attrs_blob, "filter-id"),
                "filter_cat_id": attr(attrs_blob, "filter-cat-id"),
                "title": unescape(title),
                "subtitle": unescape(subtitle),
                "description": unescape(desc),
                "image_url": HOMEPAGE + img if img and img.startswith("/") else img,
                "detail_url": absolute_url,
            }

            if deal["title"] and deal["detail_url"]:
                deals.append({k: v for k, v in deal.items() if v is not None})

    # Dedupe by detail_url (deals can appear in multiple grids on a page)
    seen = set()
    deduped = []
    for d in deals:
        if d["detail_url"] in seen:
            continue
        seen.add(d["detail_url"])
        deduped.append(d)
    return deduped


def main():
    parser = argparse.ArgumentParser(
        description="Browse TicketsAtWork ticket / attraction / event deals"
    )
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument(
        "--category",
        help="Theme-park / attraction slug (e.g. disneyland, wdw, usf, seaworld)",
    )
    grp.add_argument(
        "--section",
        choices=["events"],
        help="Live events in a destination (concerts, theater, sports)",
    )
    grp.add_argument(
        "--keyword",
        help="Free-text keyword search (uses Reflektion site search)",
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
    deals = []
    landed_url = None

    tmpdir = tempfile.mkdtemp(prefix="taw_")
    try:
        with sync_playwright() as p:
            ctx = make_browser_context(p, tmpdir)
            page = ctx.pages[0] if ctx.pages else ctx.new_page()

            if not login(page, user, pw, args.debug):
                log("login failed")
                ctx.close()
                sys.exit(2)

            if args.category:
                html = browse_category(page, args.category, args.debug)
            elif args.section == "events":
                html = browse_events(page, args.debug)
            else:
                html = search_keyword(page, args.keyword, args.debug)

            if html is None:
                log("browse failed; no HTML")
                ctx.close()
                sys.exit(3)

            raw_html = html
            landed_url = page.url
            deals = parse_deals(html)
            log(f"parsed {len(deals)} deals from {landed_url}")

            ctx.close()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    if args.raw_html_out and raw_html:
        Path(args.raw_html_out).write_text(raw_html)
        log(f"raw HTML saved: {args.raw_html_out}")

    output = {
        "category": args.category,
        "section": args.section,
        "keyword": args.keyword,
        "landed_url": landed_url,
        "deal_count": len(deals),
        "deals": deals,
    }

    if args.json:
        print(json.dumps(output, indent=2))
    else:
        if args.category:
            label = f"category '{args.category}'"
        elif args.section == "events":
            label = "live events"
        else:
            label = f"keyword '{args.keyword}'"
        print(f"\nTicketsAtWork: {label}")
        print(f"  landed: {landed_url}")
        print(f"  {len(deals)} deals")
        for d in deals[:30]:
            t = d.get("type") or "?"
            title = d.get("title", "?")
            sub = d.get("subtitle") or ""
            sub_str = f" — {sub}" if sub else ""
            print(f"    [{t}] {title}{sub_str}")
            print(f"           {d.get('detail_url', '?')}")


if __name__ == "__main__":
    main()
